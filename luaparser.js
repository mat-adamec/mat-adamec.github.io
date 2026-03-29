import fs from "fs";
import luaparse from "luaparse";

/*
DEFAULTS / CONSTANTS
*/
const IMAGE_BASE_URL =
  "https://raw.githubusercontent.com/keyboardturner/wow-ui-art/retail_png";

const ICON_LOOKUP_FILE = "https://raw.githubusercontent.com/mat-adamec/mat-adamec.github.io/refs/heads/main/icon_map.json";

const relationship_status = [
  "NA",
  "Single",
  "Taken",
  "Married",
  "Divorced",
  "Widowed",
];

/*
UTILS
*/
function badEnding(key, value) {
  console.warn(`Unrecognized key: ${key}. Unable to parse.`);
  console.warn(key);
  console.warn(value);
}

function parseIcon(name, imageBaseUrl, lookupTable) {
  const iconName = lookupTable[name];
  if (!iconName) {
    console.warn(`Icon not found in icon_map.json: ${name}`);
    return null;
  }
  return `${imageBaseUrl}/ICONS/${iconName}`;
}

function parseImage(name, imageBaseUrl) {
  if (name.startsWith("Interface\\")) {
    name = name.slice("Interface\\".length);
  }
  return `${imageBaseUrl}/${name}.png`;
}

/*
LUA AST -> JS VALUE
*/
function luaAstToJs(node) {
  if (!node) return null;

  switch (node.type) {
    case "StringLiteral":
      return node.value;

    case "NumericLiteral":
      return node.value;

    case "BooleanLiteral":
      return node.value;

    case "NilLiteral":
      return null;

    case "TableConstructorExpression": {
      const obj = {};
      let arrayIndex = 1;

      for (const field of node.fields) {
        if (field.type === "TableKeyString") {
          const key = field.key.name;
          obj[key] = luaAstToJs(field.value);
        } else if (field.type === "TableKey") {
          const key = luaAstToJs(field.key);
          obj[key] = luaAstToJs(field.value);
        } else if (field.type === "TableValue") {
          obj[arrayIndex] = luaAstToJs(field.value);
          arrayIndex++;
        } else {
          console.warn("Unknown table field type:", field.type);
        }
      }

      return obj;
    }

    default:
      console.warn("Unhandled AST node type:", node.type);
      return null;
  }
}

/*
EXTRACT GLOBALS FROM LUA FILE
*/
function extractGlobalsFromLua(luaText) {
  const ast = luaparse.parse(luaText, {
    comments: false,
    scope: false,
    locations: false,
  });

  const globals = {};

  for (const stmt of ast.body) {
    if (stmt.type !== "AssignmentStatement") continue;

    for (let i = 0; i < stmt.variables.length; i++) {
      const variable = stmt.variables[i];
      const initValue = stmt.init[i];

      if (!variable || variable.type !== "Identifier") continue;

      const name = variable.name;

      if (
        name === "TRP3_Characters" ||
        name === "TRP3_Profiles" ||
        name === "TRP3_Companions"
      ) {
        globals[name] = luaAstToJs(initValue);
      }
    }
  }

  return globals;
}

/*
FORMAT CHARACTERISTICS
*/
function formatCharacteristics(characteristics, iconLookup, imageBaseUrl) {
  const jdict = {
    basic: {},
    additional: {},
    top: {},
    sliders: [],
  };

  for (const [key, value] of Object.entries(characteristics)) {
    switch (key) {
      // Top
      case "FN":
        jdict.top["First Name"] = value;
        break;

      case "FT":
        jdict.top["Full Title"] = value;
        break;

      case "LN":
        jdict.top["Last Name"] = value;
        break;

      case "IC":
        jdict.top["Class Icon"] = parseIcon(value, imageBaseUrl, iconLookup);
        break;

      // Basic
      case "RA":
        jdict.basic["Race"] = value;
        break;

      case "CL":
        jdict.basic["Class Name"] = { value, color: characteristics["CH"] };
        break;

      case "CH":
        break;

      case "AG":
        jdict.basic["Age"] = value;
        break;

      case "EC":
        jdict.basic["Eye Color"] = { value, color: characteristics["EH"] };
        break;

      case "EH":
        break;

      case "HE":
        jdict.basic["Height"] = value;
        break;

      case "WE":
        jdict.basic["Body Shape"] = value;
        break;

      case "BP":
        jdict.basic["Birthplace"] = value;
        break;

      case "RE":
        jdict.basic["Residence"] = value;
        break;

      case "RS":
        jdict.basic["Relationship Status"] =
          relationship_status[value] ?? value;
        break;

      // Additional custom fields
      case "MI":
        for (const customCharacteristic of Object.values(value)) {
          if (!customCharacteristic) continue;

          const name = customCharacteristic["NA"];
          const icon = customCharacteristic["IC"];
          const data = customCharacteristic["VA"];

          jdict.additional[name] = {
            value: data,
            icon: parseIcon(icon, imageBaseUrl, iconLookup),
          };
        }
        break;

      // Sliders
      case "PS":
        for (const customSlider of Object.values(value)) {
          if (!customSlider) continue;

          jdict.sliders.push([
            {
              value: customSlider["LT"],
              icon: customSlider["LI"],
              color: customSlider["LC"],
            },
            customSlider["V2"],
            {
              value: customSlider["RT"],
              icon: customSlider["RI"],
              color: customSlider["RC"],
            },
          ]);
        }
        break;

      default:
        badEnding(key, value);
    }
  }

  return jdict;
}

/*
MAIN FUNCTION
*/
function parseTRP3(trp3FilePath, characterName, options = {}) {
  const imageBaseUrl = options.imageBaseUrl ?? IMAGE_BASE_URL;
  const iconLookupPath = options.iconLookupPath ?? ICON_LOOKUP_FILE;

  const luaText = fs.readFileSync(trp3FilePath, "utf-8");
  const iconLookup = JSON.parse(fs.readFileSync(iconLookupPath, "utf-8"));

  const globals = extractGlobalsFromLua(luaText);

  const characters = globals.TRP3_Characters;
  const profiles = globals.TRP3_Profiles;

  if (!characters) throw new Error("TRP3_Characters not found.");
  if (!profiles) throw new Error("TRP3_Profiles not found.");

  const charData = characters[characterName];
  if (!charData) throw new Error(`Character not found: ${characterName}`);

  const character_id = charData.profileID;
  if (!character_id) throw new Error("profileID not found for character.");

  const profile = profiles[character_id]?.player;
  if (!profile) throw new Error(`Profile not found for ID: ${character_id}`);

  const dict_characteristics = profile.characteristics;
  const dict_about = profile.about;
  const dict_glance = profile.misc?.PE;

  if (!dict_characteristics)
    throw new Error("characteristics not found in profile.");

  const formatted = formatCharacteristics(
    dict_characteristics,
    iconLookup,
    imageBaseUrl
  );

  return {
    character_name: characterName,
    character_id,
    characteristics_raw: dict_characteristics,
    about: dict_about,
    glance: dict_glance,
    formatted_characteristics: formatted,
  };
}

/*
CLI ENTRYPOINT
*/
function main() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error(
      "Usage:\n  node trp3_parser.js <path_to_totalRP3.lua> <CharacterName-Realm>\n"
    );
    process.exit(1);
  }

  const trp3Path = args[0];
  const characterName = args[1];

  const output = parseTRP3(trp3Path, characterName);

  fs.writeFileSync(
    "output_character.json",
    JSON.stringify(output, null, 2),
    "utf-8"
  );

  console.log("Wrote output_character.json");
}

main();
