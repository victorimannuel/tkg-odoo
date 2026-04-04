import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

import { computeAppsAndMenuItems, reorderApps } from "@web/webclient/menus/menu_helpers";

export const appMenuService = {
    dependencies: ["menu"],
    async start(env, { menu }) {
        return {
        	getCurrentApp () {
        		return menu.getCurrentApp();
        	},
        	getAppsMenuItems() {
				const menuItems = computeAppsAndMenuItems(
					menu.getMenuAsTree('root')
				)
				const apps = menuItems.apps;
				const menuConfig = JSON.parse(
					user.settings?.homemenu_config || 'null'
				);
				if (menuConfig) {
                    reorderApps(apps, menuConfig);
				}
        		return apps;
			},
			getAppSections(appId) {
				// console.log(menu)
				if (!appId) {
					return [];
				}
				const tree = menu.getMenuAsTree(appId);
				console.log(tree)
				return tree?.childrenTree || [];
			},
			selectApp(app) {
				menu.selectMenu(app);
			}
        };
    },
};

registry.category("services").add("app_menu", appMenuService);
