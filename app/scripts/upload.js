import ftp from "basic-ftp";
import fs from "fs";
import path from "path";

// load .env file
import dotenv from "dotenv";
dotenv.config();

// configure ftp lib
const config = {
  host: "",
  user: "",
  password: "",
  path: "",
  secure: true, // true = explicit FTPS, "implicit" = implicit FTPS
  secureOptions: {
    rejectUnauthorized: false, // set to true in production with valid certs
  },
};

// configure passwords
if (process.env.TARGET === "preview") {
  config.host = process.env.PREVIEW_FTP_HOST;
  config.user = process.env.PREVIEW_FTP_USER;
  config.password = process.env.PREVIEW_FTP_PASSWORD;
  config.path = process.env.PREVIEW_FTP_PATH;
} else {
  config.host = process.env.FTP_HOST;
  config.user = process.env.FTP_USER;
  config.password = process.env.FTP_PASSWORD;
  config.path = process.env.FTP_PATH;
}

// Directories
const DIST_DIR = path.resolve("dist");

// Welcome message
console.log("");
console.log(
  `Start upload to control server, HOST: ${config.host}, Source: ${DIST_DIR}  Server path: ${process.env.FTP_PATH}`,
);

const uploadFolder = async (localFolder, remoteFolder) => {
  const client = new ftp.Client();
  // client.ftp.verbose = true;

  try {
    await client.access(config);

    console.log("Connected to FTPS server");

    // Ensure remote folder exists
    await client.ensureDir(remoteFolder);
    // await client.clearWorkingDir();

    await uploadRecursive(client, localFolder);

    console.log("Upload complete ✅");
  } catch (err) {
    console.error("Upload failed ❌", err);
  } finally {
    client.close();
  }
};

// helper function to recursively upload the contents of a folder
const uploadRecursive = async (client, localPath) => {
  const items = fs.readdirSync(localPath);

  for (const item of items) {
    const fullPath = path.join(localPath, item);
    const stats = fs.statSync(fullPath);

    // omit .vite dir
    if (stats.isDirectory() && item === ".vite") {
      continue;
    }

    if (stats.isDirectory()) {
      await client.ensureDir(item);
      await uploadRecursive(client, fullPath);
      await client.cd("..");
    } else {
      console.log(`Uploading ${fullPath}`);
      await client.uploadFrom(fullPath, item);
    }
  }
};

await uploadFolder(DIST_DIR, config.path);
