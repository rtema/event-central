import fs from "fs";
import path from "path";

// Welcome message
console.log("Cleaning output dirs");

// helper function to delete the contents of a folder
const deleteFolderContents = (dir) => {
  if (!fs.existsSync(dir)) {
    console.log(`📂 Folder ${dir} does not exist`);
    return;
  }

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    fs.rmSync(path.join(dir, entry.name), { recursive: true });
  }

  console.log(`📂 Cleaned files from ${dir}`);
};

// clean output dirs
deleteFolderContents(path.join(path.resolve("dist")));

// Empty line for nicer console output during build
console.log("");
