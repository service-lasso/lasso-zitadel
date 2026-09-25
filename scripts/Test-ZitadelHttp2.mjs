import { readFileSync } from "node:fs";
import { connect } from "node:http2";

const caPath = process.argv[2];
const issuer = (process.argv[3] ?? "https://localhost:18084").replace(/\/$/, "");

if (!caPath) {
  throw new Error("Usage: node Test-ZitadelHttp2.mjs <root-ca-path> [issuer]");
}

const ca = readFileSync(caPath);
const client = connect(issuer, { ca, ALPNProtocols: ["h2"] });

try {
  await new Promise((resolve, reject) => {
    client.once("connect", resolve);
    client.once("error", reject);
  });
  if (client.alpnProtocol !== "h2") {
    throw new Error(`ZITADEL negotiated ${client.alpnProtocol ?? "no protocol"} instead of h2.`);
  }

  const response = await new Promise((resolve, reject) => {
    const request = client.request({ ":path": "/debug/ready" });
    let status = 0;
    const chunks = [];
    request.once("response", (headers) => { status = Number(headers[":status"]); });
    request.on("data", (chunk) => chunks.push(chunk));
    request.once("end", () => resolve({ status, body: Buffer.concat(chunks).toString("utf8") }));
    request.once("error", reject);
    request.end();
  });
  if (response.status !== 200 || response.body.trim().replace(/^"|"$/g, "") !== "ok") {
    throw new Error("ZITADEL readiness failed over HTTP/2.");
  }
  process.stdout.write(JSON.stringify({ outcome: "verified", protocol: "h2", readiness: 200 }) + "\n");
} finally {
  client.close();
}
