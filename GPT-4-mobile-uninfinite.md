// ==UserScript==
// @name         Talk to ChatGPT Mobile
// @name:zh-CN   与 GPT 移动版畅聊
// @namespace    https://github.com/Unintendedz/talk-to-gpt-4-mobile
// @version      0.5
// @description  Converse with the gpt-4-mobile model on the web (without the limit of 25 messages every 3 hours that GPT-4 currently has).
// @description:zh-CN 在网页端与 gpt-4-mobile 模型进行对话（没有每3小时25条的限制）。
// @author       Unintendedz, onepisYa
// @match        https://chat.openai.com/*
// @grant        GM_registerMenuCommand
// @grant        GM_unregisterMenuCommand
// @grant        GM_addValueChangeListener
// @grant        GM_getValue
// @grant        GM_setValue
// @run-at       document-idle
// @license      WTFPL
// ==/UserScript==

(() => {
  "use strict";

  let languages = {
    en: {
        defaultModel: 'Default Model',
        otherFunctions: 'Other Functions',
        disableModeration: 'Disable moderations'
    },
    zh: {
        defaultModel: '默认模型',
        otherFunctions: '其它功能',
        disableModeration: '防止审查标记和屏蔽'
    }
  };

  class GptMobile {
    constructor() {
      this.observer = null;
      this.models = {
        "text-davinci-002-render-sha-mobile": {
          category: "gpt_3.5",
          human_category_name: "GPT-3.5 Mobile",
          subscription_level: "free",
          default_model: "text-davinci-002-render-sha-mobile",
        },
        "gpt-4-mobile": {
          category: "gpt_4",
          human_category_name: "GPT-4 Mobile",
          subscription_level: "plus",
          default_model: "gpt-4-mobile",
        },
      };
      this.resolveIsPlus = null;
      this.isPlus = new Promise((resolve) => {
        this.resolveIsPlus = resolve;
      });
      this.commands = {};
      this.moderationDisabled = GM_getValue("moderation_disabled", false);
    }

    get i18n() { 
        return navigator.language.slice(0, 2) === 'zh' ? languages['zh'] : languages['en'];
    }

    get modelsNameArray() {
      return Object.values(this.models).map(
        (model) => model.human_category_name
      );
    }

    updateMenu = () => {
      let defaultModel = GM_getValue("default_model", "fetching");
      console.log("defaultModel:", defaultModel);

      for (let command in this.commands) {
        GM_unregisterMenuCommand(this.commands[command]);
      }

      this.commands["default_model_divider"] = GM_registerMenuCommand(
        `========${this.i18n.defaultModel}========`,
        () => {}
      );
      for (let modelName in this.models) {
        let humanCategoryName = this.models[modelName].human_category_name;
        if (defaultModel === "fetching") {
          humanCategoryName += " loading";
        } else if (modelName === defaultModel) {
          humanCategoryName = `✅ ${humanCategoryName}`;
        } else {
          humanCategoryName = `⬛ ${humanCategoryName}`;
        }
        this.commands[modelName] = GM_registerMenuCommand(
          humanCategoryName,
          () => {
            console.log("on select modelName:", modelName);
            if (defaultModel !== "fetching") {
              GM_setValue("default_model", modelName);
              unsafeWindow.location.href = `/?model=${modelName}`;
            }
          }
        );
      }

      this.commands["other_functions_divider"] = GM_registerMenuCommand(
        `========${this.i18n.otherFunctions}========`,
        () => {}
      );
      this.commands["moderation_disabled"] = GM_registerMenuCommand(
        `${this.moderationDisabled ? "✅" : "⬛"} ${this.i18n.disableModeration}`,
        () => {
          this.moderationDisabled = !this.moderationDisabled;
          GM_setValue("moderation_disabled", this.moderationDisabled);
          this.updateMenu();
        }
      );
    };

    registerValueChangeHandler = () => {
      GM_addValueChangeListener(
        "default_model",
        (name, old_value, new_value, remote) => {
          this.updateMenu();
        }
      );
      GM_addValueChangeListener(
        "moderation_disabled",
        (name, old_value, new_value, remote) => {
          this.moderationDisabled = new_value;
        }
      );
    };

    responseHandlers = () => {
      return {
        "https://chat.openai.com/backend-api/accounts/check": async (
          response
        ) => {
          const body = await response.clone().json();
          const subscription_plan =
            body.accounts.default.entitlement.subscription_plan;
          const isPlusPlan = subscription_plan === "chatgptplusplan";
          this.resolveIsPlus(isPlusPlan);
          if (GM_getValue("default_model") === undefined) {
            const defaultModel = isPlusPlan
              ? "gpt-4-mobile"
              : "text-davinci-002-render-sha-mobile";
            GM_setValue("default_model", defaultModel);
          }
          return response;
        },
        "https://chat.openai.com/backend-api/models": async (response) => {
          const body = await response.clone().json();
          const defaultModel = GM_getValue("default_model");
          let model;
          if (!defaultModel) {
            model = (await this.isPlus)
              ? this.models["gpt-4-mobile"]
              : this.models["text-davinci-002-render-sha-mobile"];
          } else {
            model = this.models[defaultModel];
          }
          body.categories.push(model);
          return new Response(JSON.stringify(body), {
            status: response.status,
            statusText: response.statusText,
            headers: { "Content-Type": "application/json" },
          });
        },
        "https://chat.openai.com/backend-api/moderations": async (response) => {
          console.log(
            'GM_getValue("moderation_disabled"):',
            GM_getValue("moderation_disabled")
          );
          const body = await response.clone().json();
          if (GM_getValue("moderation_disabled")) {
            body.flagged = false;
            body.blocked = false;
          }
          return new Response(JSON.stringify(body), {
            status: response.status,
            statusText: response.statusText,
            headers: { "Content-Type": "application/json" },
          });
        },
      };
    };

    setupFetchProxy = () => {
      unsafeWindow.fetch = new Proxy(window.fetch, {
        apply: async (target, thisArg, argumentsList) => {
          const response = await Reflect.apply(target, thisArg, argumentsList);
          for (let key in this.responseHandlers()) {
            if (argumentsList[0].includes(key)) {
              return this.responseHandlers()[key](response);
            }
          }
          return response;
        },
      });
    };

    setupModelObserver = () => {
      const modelName =
        this.models[GM_getValue("default_model")].human_category_name;
      const observer = new MutationObserver((mutationsList, observer) => {
        for (let mutation of mutationsList) {
          if (mutation.type === "childList") {
            const modelElement = document.evaluate(
              `//span[contains(text(), "${modelName}")]`,
              document,
              null,
              XPathResult.FIRST_ORDERED_NODE_TYPE,
              null
            ).singleNodeValue;
            if (modelElement) {
              modelElement.click();
              observer.disconnect();
            }
          }
        }
      });

      observer.observe(document, { childList: true, subtree: true });
    };

    onUrlStateChange = (target, thisArg, argArray) => {
      let oldUrl = new URL(window.location.href);
      let newUrl = new URL(argArray[2], window.location.origin);
      let currentModel = newUrl.searchParams.get("model");
      if (currentModel) {
        let expectedModel = GM_getValue("default_model");
        if (currentModel !== expectedModel) {
          newUrl.searchParams.set("model", expectedModel);
        }
        argArray[2] = newUrl.toString();
      }
      let result = target.apply(thisArg, argArray);
      if (newUrl.pathname === "/" && oldUrl.pathname !== "/") {
        this.setupModelObserver();
      } else if (newUrl.pathname === "/" && !newUrl.search) {
        newUrl.searchParams.set("model", GM_getValue("default_model"));
        this.setupModelObserver();
      }
      return result;
    };

    setupHistoryProxy = () => {
      unsafeWindow.history.pushState = new Proxy(
        unsafeWindow.history.pushState,
        {
          apply: (target, thisArg, argArray) => {
            return this.onUrlStateChange(target, thisArg, argArray);
          },
        }
      );

      unsafeWindow.history.replaceState = new Proxy(
        unsafeWindow.history.replaceState,
        {
          apply: (target, thisArg, argArray) => {
            return this.onUrlStateChange(target, thisArg, argArray);
          },
        }
      );
    };

    init = () => {
      this.updateMenu();
      this.registerValueChangeHandler();
      this.setupFetchProxy();
      this.setupHistoryProxy();
      this.setupModelObserver();
    };
  }

  const gptMobile = new GptMobile();
  gptMobile.init();
})();
