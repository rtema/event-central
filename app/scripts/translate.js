import fs from "fs";
import path from "path";
import * as deepl from "deepl-node";
import * as gettextParser from "gettext-parser";

// load .env file
import dotenv from "dotenv";
dotenv.config();

const authKey = process.env.DEEPL_API_KEY;
const translator = new deepl.Translator(authKey);

const LOCALES_DIR = "src/locales";
const SOURCE_LOCALE = "EN";

async function translateLocale(lang, targetLocale) {
  try {
    if (targetLocale === SOURCE_LOCALE) {
      return;
    }

    const inputFile = path.join(LOCALES_DIR, `${lang}.po`);
    console.log(`Reading ${inputFile}...`);
    const input = fs.readFileSync(inputFile);
    const po = gettextParser.po.parse(input);

    // We will collect promises to run translations in parallel where possible
    const translationJobs = [];
    const contextMap = []; // To keep track of which ID belongs to which translation

    // Iterate over the translations object
    // The structure is usually po.translations[context][msgid]
    for (const context in po.translations) {
      for (const msgid in po.translations[context]) {
        const entry = po.translations[context][msgid];

        // Skip the header entry (empty msgid)
        if (msgid === "") continue;

        // Check if translation is missing (msgstr is empty or same as ID)
        // You can adjust this logic depending on your needs (e.g., force re-translate)
        const currentTranslation = entry.msgstr[0];
        if (!currentTranslation) {
          // Add to job list
          translationJobs.push(entry.msgid);
          contextMap.push({ context, msgid });
        }
      }
    }

    if (translationJobs.length === 0) {
      console.log("No untranslated strings found.");
      return;
    }

    console.log(
      `Translating ${translationJobs.length} strings to ${targetLocale}...`,
    );

    // Send to DeepL
    // Note: DeepL accepts arrays of strings, which is more efficient than single requests
    const results = await translator.translateText(
      translationJobs,
      SOURCE_LOCALE,
      targetLocale,
    );

    // Map results back to the PO object
    results.forEach((result, index) => {
      const { context, msgid } = contextMap[index];

      // Update the msgstr with the translation
      po.translations[context][msgid].msgstr = [result.text];

      // Optional: Remove 'fuzzy' flag if present, as it is now machine translated
      if (
        po.translations[context][msgid].comments &&
        po.translations[context][msgid].comments.flag
      ) {
        po.translations[context][msgid].comments.flag = po.translations[
          context
        ][msgid].comments.flag
          .replace("fuzzy", "")
          .trim();
      }
    });

    console.log(`Writing to ${inputFile}...`);
    const output = gettextParser.po.compile(po);
    fs.writeFileSync(inputFile, output);

    console.log("Done! Translation complete.");
  } catch (error) {
    console.error("An error occurred during translation:", error);
  }
}

await (async () => {
  for (const locale of [
    ["en", "EN"],
    ["de", "DE"],
  ]) {
    await translateLocale(...locale);
  }
})();
