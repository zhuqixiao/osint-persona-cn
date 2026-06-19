const OSINTConfig = {
  extVersion: "0.3.1",
  defaultApiBase: "http://127.0.0.1:8787",
  async getApiBase() {
    return new Promise((resolve) => {
      chrome.storage.local.get(["apiBase"], (data) => {
        resolve(data.apiBase || OSINTConfig.defaultApiBase);
      });
    });
  },
};
