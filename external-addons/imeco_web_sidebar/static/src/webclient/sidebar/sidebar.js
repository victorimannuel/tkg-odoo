import { url } from '@web/core/utils/urls';
import { useService } from '@web/core/utils/hooks';
import { user } from "@web/core/user";
import { browser } from '@web/core/browser/browser';

import { Component, onWillUnmount, useState } from '@odoo/owl';

export class SideBar extends Component {
	static template = 'imeco_web_sidebar.SideBar';
    static props = {};
	setup() {
        this.state = useState({ hoveredSectionId: null });
        this.appMenuService = useService('app_menu');
        this.hidePopupTimeout = null;
        this.currentActionId = null;
        this.isTouchDevice =
            typeof window !== "undefined" &&
            ("ontouchstart" in window ||
                (window.navigator &&
                    (window.navigator.maxTouchPoints > 0 ||
                        window.navigator.msMaxTouchPoints > 0)));
        this.hidePopupTimeout = null;
    	if (user.activeCompany.has_sidebar_image) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'sidebar_image',
                id: user.activeCompany.id,
            });
    	}
        this.popupHover = false;
        this.popupEl = document.createElement("div");
        this.popupEl.className = "sidebar_apps_submenu_popup";
        this.popupEl.style.display = "none";
        document.body.appendChild(this.popupEl);
        this.popupEl.addEventListener("mouseenter", () => {
            this.popupHover = true;
        });
        this.popupEl.addEventListener("mouseleave", () => {
            this.popupHover = false;
            this._hideSubmenuPopup();
        });

    	const renderAfterMenuChange = () => {
            this.render();
        };
        this.env.bus.addEventListener(
        	'MENUS:APP-CHANGED', renderAfterMenuChange
        );
        this.env.bus.addEventListener(
            'ACTION_MANAGER:UI-UPDATED', renderAfterMenuChange
        );
        onWillUnmount(() => {
            this.env.bus.removeEventListener(
            	'MENUS:APP-CHANGED', renderAfterMenuChange
            );
            this.env.bus.removeEventListener(
                'ACTION_MANAGER:UI-UPDATED', renderAfterMenuChange
            );
            if (this.popupEl && this.popupEl.parentNode) {
                this.popupEl.parentNode.removeChild(this.popupEl);
            }
        });
    }
    _isSectionActive(section) {
        if (!this.currentActionId) {
            return false;
        }
        const containsAction = (menu, actionId) => {
            if (!menu) {
                return false;
            }
            if (menu.actionID === actionId) {
                return true;
            }
            if (menu.childrenTree && menu.childrenTree.length) {
                for (const child of menu.childrenTree) {
                    if (containsAction(child, actionId)) {
                        return true;
                    }
                }
            }
            return false;
        };
        return containsAction(section, this.currentActionId);
    }

    _getFirstActionableMenu(menu) {
        if (!menu) {
            return null;
        }
        if (menu.actionID) {
            return menu;
        }
        if (menu.childrenTree && menu.childrenTree.length) {
            for (const child of menu.childrenTree) {
                const actionable = this._getFirstActionableMenu(child);
                if (actionable) {
                    return actionable;
                }
            }
        }
        return null;
    }
    _onSectionClick(section) {
        if (!section) {
            return;
        }
        let target = section;
        if (section.childrenTree && section.childrenTree.length) {
            const firstActionable = this._getFirstActionableMenu(section);
            if (firstActionable) {
                target = firstActionable;
            } else {
                return;
            }
        }
        if (target.actionID) {
            this.currentActionId = target.actionID;
            this.render();
            this.appMenuService.selectApp(target);
        }
    }
    _showSubmenuPopup(section, target) {
        if (!this.popupEl) {
            return;
        }
        if (!section || !section.childrenTree || !section.childrenTree.length) {
            this._hideSubmenuPopup();
            return;
        }
        while (this.popupEl.firstChild) {
            this.popupEl.removeChild(this.popupEl.firstChild);
        }
        const listEl = document.createElement("ul");
        listEl.className = "sidebar_apps_submenu_popup_list";
        const addItems = (menu, level) => {
            if (!menu.childrenTree || !menu.childrenTree.length) {
                return;
            }
            for (const child of menu.childrenTree) {
                const itemEl = document.createElement("li");
                const isActionable = !!child.actionID;
                itemEl.className = "sidebar_apps_submenu_popup_item" + (isActionable ? " sidebar_apps_submenu_popup_item--actionable" : " sidebar_apps_submenu_popup_item--section");
                itemEl.textContent = child.name;
                itemEl.style.paddingLeft = `${8 + level * 12}px`;
                if (isActionable) {
                    itemEl.addEventListener("click", (ev) => {
                        ev.preventDefault();
                        ev.stopPropagation();
                        this.currentActionId = child.actionID;
                        this.render();
                        this.appMenuService.selectApp(child);
                        this._hideSubmenuPopup();
                    });
                }
                listEl.appendChild(itemEl);
                addItems(child, level + 1);
            }
        };
        addItems(section, 0);
        this.popupEl.appendChild(listEl);
        const rect = target.getBoundingClientRect();
        const top = rect.top;
        const left = rect.right + 8;
        this.popupEl.style.top = `${top}px`;
        this.popupEl.style.left = `${left}px`;
        this.popupEl.style.display = "block";
    }
    _hideSubmenuPopup() {
        if (this.popupEl) {
            this.popupEl.style.display = "none";
        }
    }
    _onRootSectionEnter(section, target) {
        if (!section) {
            this._hideSubmenuPopup();
            return;
        }
        if (this.hidePopupTimeout) {
            clearTimeout(this.hidePopupTimeout);
            this.hidePopupTimeout = null;
        }
        this._showSubmenuPopup(section, target);
    }
    _onRootSectionLeave() {
        if (this.isTouchDevice) {
            return;
        }
        if (this.hidePopupTimeout) {
            clearTimeout(this.hidePopupTimeout);
        }
        this.hidePopupTimeout = setTimeout(() => {
            if (!this.popupHover) {
                this._hideSubmenuPopup();
            }
            this.hidePopupTimeout = null;
        }, 50);
    }
    _onSidebarLeave() {
        this._hideSubmenuPopup();
    }
}
