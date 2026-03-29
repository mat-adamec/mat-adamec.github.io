from pathlib import Path
from lupa import LuaRuntime
import re
import string
import json
from collections import OrderedDict

trp3_file = Path("E:/Games/Battle.net Games/World of Warcraft/_retail_/WTF/Account/72094383#1/SavedVariables/totalRP3.lua")
image_files = Path("https://raw.githubusercontent.com/keyboardturner/wow-ui-art/retail_png/")
icon_lookup_table = Path("icon_map.json")
stylesheet = Path('style.css')
character_name = "Terawyne-MoonGuard"

''' KEY NOTES
Organized as:
    TRP3_Profiles[numerical identifier][player][chracteristics] (main)
    TRP3_Profiles[numerical identifier][player][about] (description)
    TRP3_Profiles[numerical identifier][player][misc][PE][1-5] (quick glance)
    
FN = first name
FT = full titlle
RE = residence
RS = relationship status
custom get ID, NA (name), VA (value), IC (icon)
sliders get RT (right name), V2 (number), RC (right color, b g and r), LT (left name), LC (left color, b g and r), LI (left icon) and RI (right icon)
'''

relationship_status = ['NA', 'Single', 'Taken', 'Married', 'Divorced', 'Widowed']
orientation_dict = {'c': "center", 'l': "left", 'r': "right"}

lua = LuaRuntime(unpack_returned_tuples=True)

with open(trp3_file, 'r', encoding="utf-8") as trp3:
    lua.execute(trp3.read())

lua_characters = lua.globals().TRP3_Characters
lua_companions = lua.globals().TRP3_Companions
lua_profiles = lua.globals().TRP3_Profiles

def lua_to_python(obj):
    if isinstance(obj, dict):          # already a Python dict
        return {k: lua_to_python(v) for k, v in obj.items()}
    if hasattr(obj, 'items'):          # LuaTable
        return {k: lua_to_python(v) for k, v in dict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [lua_to_python(item) for item in obj]
    return obj   # numbers, strings, bool, None, etc.

characters = lua_to_python(lua_characters)
companions = lua_to_python(lua_companions)
profiles = lua_to_python(lua_profiles)

character_id = characters[character_name]['profileID']
dict_characteristics = profiles[character_id]['player']['characteristics']
dict_about = profiles[character_id]['player']['about']
dict_glance = profiles[character_id]['player']['misc']['PE']

with open(icon_lookup_table, 'r', encoding="utf-8") as lookup:
    icon_lookup = json.load(lookup)

###

def bad_ending(key: str, value: str) -> None:
    print(f"Unrecognized key: {key}. Unable to parse. Please report this to Terawyne!")
    print(f"{key}")
    print(f"{value}")
    
def parse_icon(name: str, blizzard_art: Path = image_files, lookup_table: Path = icon_lookup) -> Path:
    icon_path = blizzard_art / 'ICONS'
    name = lookup_table[name]
    return icon_path / name

def parse_image(name: str, blizzard_art: Path = image_files) -> Path:
    # Drop leading 'interface'.
    name = name.removeprefix('Interface\\')
    return blizzard_art / (name + '.png')

def format_characteristics(characteristics=dict_characteristics) -> dict:
    jdict = {'basic': OrderedDict(), 'additional': OrderedDict(), 'top': OrderedDict(), 'sliders': []}
    for key, value in characteristics.items():
        match key:
            # Top
            case 'FN':
                jdict['top']['First Name'] = value
            case 'FT':
                jdict['top']['Full Title'] = value
            case 'LN':
                jdict['top']['Last Name'] = value
            case 'IC':
                jdict['top']['Class Icon'] = parse_icon(value)
            # Basic
            case 'RA':
                jdict['basic']['Race'] = value
            case 'CL':
                jdict['basic']['Class Name'] = {'value': value, 'color': characteristics['CH']}
            case 'CH':
                pass
            case 'AG':
                jdict['basic']['Age'] = value
            case 'EC':
                jdict['basic']['Eye Color'] = {'value': value, 'color': characteristics['EH']}
            case 'EH':
                pass
            case 'HE':
                jdict['basic']['Height'] = value
            case 'WE':
                jdict['basic']['Body Shape'] = value
            case 'BP':
                jdict['basic']['Birthplace'] = value
            case 'RE':
                jdict['basic']['Residence'] = value
            case 'RS':
                jdict['basic']['Relationship Status'] = relationship_status[value]
            # Additional
            case 'MI':
                for custom_characteristic in value.values():
                    name = custom_characteristic['NA']
                    icon = custom_characteristic['IC']
                    data = custom_characteristic['VA']
                    jdict['additional'][name] = {'value': data, 'icon': parse_icon(icon)}
            # Sliders
            case 'PS':
                jdict['Sliders'] = []
                for custom_slider in value.values():
                    left_name, right_name = custom_slider['LT'], custom_slider['RT']
                    left_icon, right_icon = custom_slider['LI'], custom_slider['RI']
                    left_color, right_color = custom_slider['LC'], custom_slider['RC']
                    slider_value = custom_slider['V2']
                    jdict['sliders'].append(({'value': left_name, 'icon': left_icon, 'color': left_color}, slider_value, {'value': right_name, 'icon': right_icon, 'color': right_color}))
            case _:
                bad_ending(key, value)
    return jdict

class BraceReformatter():
    registry = {}
    
    def __init__(self, data):
        self.data = data
        
    @staticmethod
    def find_braces(data):
        if not data:
            return []
        
        # Non-greedy match with DOTALL so it works across multiple lines
        pattern = r'(\{.*?\})'
        matches = re.findall(pattern, data, re.DOTALL)
        return matches
    
    @classmethod
    def reformat_brace(cls, block: str):
        if not block or len(block) < 3:
            return False
        if block in cls.registry:
            # Skip processing if already encountered.
            return cls.registry[block]
        inner = block[1:-1].strip()
        reblock = ""
        if inner.lower().startswith('img:'):
            reblock += "<img src=\""
            tag = inner.split(':')
            if len(tag) == 2:
                img, path = tag
                reblock += f"{parse_image(path)}\">"
            elif len(tag) == 4:
                img, path, width, height = tag
                reblock += f"{parse_image(path)}\" width=\"{width}\" height=\"{height}\" style=\"display:block;margin-right:auto;margin-left:auto\">"
            elif len(tag) == 5:
                img, path, width, height, orient = tag
                reblock += f"{parse_image(path)}\" width=\"{width}\" height=\"{height}\""
                if orient == 'l':
                    reblock += "style=\"display:block;margin-right:auto;\">"
                elif orient == 'c':
                    reblock += "style=\"display:block;margin-right:auto;margin=left:auto;\">"
                elif orient == 'r':
                    reblock += "style=\"display:block;margin-left:auto;\">"
                else:
                    raise ValueError(f"orientation should be 'c', 'l', or 'r', got {orient}.")
            else:
                raise ValueError(f"img tag requires 2, 4, or 5 components, broken down as img:path:(length:width):orientation. Received {tag} of length {len(tag)}")
        elif inner.lower().startswith('col:'):
            col, hexcode = inner.split(':')
            reblock += f"<span class=\"fixed-color\" style=\"color:#{hexcode};margin:0;padding:0;display:inline;\">"
        elif inner.lower().startswith('icon:'):
            reblock += "<img src=\""
            tag = inner.split(':')
            if len(tag) == 2:
                img, path = tag
                reblock += f"{parse_icon(path)}\">"
            elif len(tag) == 3:
                img, path, size = tag
                reblock += f"{parse_icon(path)}\" width=\"{size}\" height=\"{size}\">"
            else:
                raise ValueError(f"icon tag requires 2 or 3 components, broken down as img:path:square_size. Received {tag} of length {len(tag)}")
        elif inner.lower().startswith('link*'):
            a, href, text = inner.split('*')
            reblock += f"<a href=\"{href}\">{text}</a>"
        elif inner.lower().startswith('p'):
            tag = inner.split(':')
            if len(tag) == 1:
                reblock += "<p>"
            elif len(tag) == 2:
                reblock += f"<p style=\"text-align:{orientation_dict[tag[-1]]}\">"
            else:
                raise ValueError(f"p tag requires 1 or 2 components, broken down as p:orientation. Received {tag} of length {len(tag)}")
        elif inner.lower().startswith('h'):
            tag = inner.split(':')
            if len(tag) == 1:
                reblock += f"<{tag[0]}>"
            elif len(tag) == 2:
                reblock += f"<{tag[0]} style=\"text-align:{orientation_dict[tag[-1]]}\">"
            else:
                raise ValueError(f"{tag[0]} tag requires 1 or 2 components, broken down as {tag[0]}:orientation. Received {tag} of length {len(tag)}")
        elif inner.lower().startswith('/'):
            if inner != '/col':
                reblock += f"<{inner}>"
            else:
                reblock += f"</span>"
        else:
            split = inner.split(':')
            bad_ending(split[0], ':'.join(split[1:]))
            return False
        cls.registry[block] = reblock
        return reblock
                
    def reformat_braces(self):
        blocks = BraceReformatter.find_braces(self.data)
        out = self.data
        for block in blocks:
            reblock = self.reformat_brace(block)
            if reblock is not False:
                out = out.replace(block, reblock, 1)
        return out
            
            
def format_about(about=dict_about) -> str:
    about = dict_about['T1']['TX'].replace('𝔼', '')
    formatter = BraceReformatter(about)
    formatted = formatter.reformat_braces()
    return formatted

def html_background():
    return f"<head><link rel=\"stylesheet\" href=\"{stylesheet}\"</head>"
class FormatCharacteristics:
    def __init__(self, cdict):
        self.basic = cdict['basic']
        self.additional = cdict['additional']
        self.sliders = cdict['sliders']
        self.top = cdict['top']
        self.html = ""

    def format_fields(self, name, value, icon=None, color=None):
        # Icon (Optional) | Field _ Color (Optional) | Value
        if icon and color:
            return f"""
                <div class="info-row">
                    <div class="info-left">
                        <span><img src={icon} class="icon" alt=""/></span>
                        <span class="name">{name}</span>
                    </div>
                    <div class="info-right">
                        <span class="color-box" style="background-color:{color};"</span>
                        <span class="value">{value}</span>
                    </div>
                </div>
            """
        elif icon:
            return f"""
                <div class="info-row">
                    <div class="info-left">
                        <span class="icon"><img src={icon} alt=""/></span>
                        <span class="name">{name}</span>
                    </div>
                    <div class="info-right">
                        <span class="color-box"></span>
                        <span class="value">{value}</span>
                    </div>
                </div>
            """
        elif color:
            return f"""
                <div class="info-row">
                    <div class="info-left">
                        <span class="icon"></span>
                        <span class="name">{name}</span>
                    </div>
                    <div class="info-right">
                        <span class="color-box" style="background-color:{color};"></span>
                        <span class="name">{value}</span>
                    </div>
                </div>
            """
        else:
            return f"""
                <div class="info-row">
                    <div class="info-left">
                        <span class="icon"></span>
                        <span class="name">{name}</span>
                    </div>
                    <div class="info-right">
                        <span class="color-box"></span>
                        <span class="value">{value}</span>
                    </div>
                </div>
            """
    
    def format_sliders(self, lname, licon, lcolor, val, rname, ricon, rcolor):
        return f"""
            <div class="slider-row">
                <div class="slider-left">
                    <span class="name">{lname}</span>
                    <span class="icon"><img src="{licon}"/></span>
                </div>
                <div class="slider-val">
                    <span class="slider" style="--ticks: 20; --filled: {val}; --left-color: rgb({lcolor['r']*255}, {lcolor['g']*255}, {lcolor['b']*255}); --right-color: rgb({rcolor['r']*255}, {rcolor['g']*255}, {rcolor['b']*255});"></span>
                </div>
                <div class="slider-right">
                    <span class="icon"><img src="{ricon}">/</span>
                    <span class="name">{rname}</span>
                </div>
            </div>
        """
        
    def format_top(self):
        ...
        
    def format_basic(self):
        self.html += "<div class=\"info-box\">"
        for field in self.basic:
            if isinstance(self.basic[field], dict):
                self.html += self.format_fields(name=field, **self.basic[field])
            else:
                self.html += self.format_fields(name=field, value=self.basic[field])
        self.html += "</div>"
        
    def format_additional(self):
        self.html += "<div class=\"info-box\">"
        for field in self.additional:
            if isinstance(self.additional[field], dict):
                self.html += self.format_fields(name=field, **self.additional[field])
            else:
                self.html += self.format_fields(name=field, value=self.additional[field])
        self.html += "</div>"
        
    def format_slide(self):
        self.html += "<div class=\"info-box\">"
        for left, val, right in self.sliders:
            lname, licon, lcolor = left.values()
            rname, ricon, rcolor = right.values()
            self.html += self.format_sliders(lname, parse_icon(licon), lcolor, val, rname, parse_icon(ricon), rcolor)
        self.html += "</div>"

cdict = format_characteristics()
cformatter = FormatCharacteristics(cdict)
cformatter.format_basic()
cformatter.format_additional()
cformatter.format_slide()
with open('characteristics.html', 'w', encoding='utf-8') as html:
    html.write(html_background() + cformatter.html)

astr = format_about()
with open('about.html', 'w', encoding='utf-8') as html:
    html.write(html_background() + astr)