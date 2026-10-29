#!/usr/bin/env node
/* Regressões da exceção HTTP local usada apenas por prebuild/CNG. */
const assert = require("node:assert/strict");
const path = require("node:path");

const appJson = require("../src/frontend/smart-parking/app.json");
const plugin = require("../src/frontend/smart-parking/plugins/withLocalNetwork");
const { hostsLocaisDoAmbiente, xmlRedeLocal } = plugin;

let total = 0;
function test(nome, fn) {
  fn();
  total += 1;
  console.log(`✔ ${nome}`);
}

test("app.json não contém ATS arbitrário nem cleartext Android global", () => {
  const ats = appJson.expo.ios.infoPlist.NSAppTransportSecurity;
  assert.notEqual(ats.NSAllowsArbitraryLoads, true);
  const buildProperties = appJson.expo.plugins.find(
    (item) => Array.isArray(item) && item[0] === "expo-build-properties",
  );
  assert.equal(buildProperties[1].android.usesCleartextTraffic, false);
  assert.ok(appJson.expo.plugins.includes("./plugins/withLocalNetwork"));
});

test("prebuild deriva somente o host privado da URL mobile efetiva", () => {
  assert.deepEqual(
    hostsLocaisDoAmbiente({
      EXPO_PUBLIC_API_URL_MOBILE: "http://192.168.1.44:8000/",
      EXPO_PUBLIC_API_URL: "http://10.0.0.8:8000",
    }),
    ["192.168.1.44"],
  );
  assert.deepEqual(
    hostsLocaisDoAmbiente({ EXPO_PUBLIC_API_URL: "http://10.0.2.2:8000" }),
    ["10.0.2.2"],
  );
  assert.deepEqual(
    hostsLocaisDoAmbiente({ EXPO_PUBLIC_API_URL_MOBILE: "http://169.254.0.21:8000" }),
    ["169.254.0.21"],
  );
  assert.deepEqual(
    hostsLocaisDoAmbiente({ EXPO_PUBLIC_API_URL_MOBILE: "https://api.example.com" }),
    [],
  );
});

test("HTTP público e hosts disfarçados falham antes do build nativo", () => {
  for (const url of [
    "http://api.example.com",
    "http://192.168.1.44.evil.example:8000",
    "http://172.32.0.1:8000",
  ]) {
    assert.throws(
      () => hostsLocaisDoAmbiente({ EXPO_PUBLIC_API_URL_MOBILE: url }),
      /HTTP público/,
    );
  }
});

test("network-security-config é fechado sem host e cirúrgico com host", () => {
  const fechado = xmlRedeLocal([]);
  assert.match(fechado, /<base-config cleartextTrafficPermitted="false"/);
  assert.doesNotMatch(fechado, /<domain-config/);

  const local = xmlRedeLocal(["192.168.1.44"]);
  assert.match(local, /<base-config cleartextTrafficPermitted="false"/);
  assert.match(
    local,
    /<domain includeSubdomains="false">192\.168\.1\.44<\/domain>/,
  );
  assert.doesNotMatch(local, /includeSubdomains="true"/);
});

console.log(`Rede local nativa: ${total} grupos OK`);
