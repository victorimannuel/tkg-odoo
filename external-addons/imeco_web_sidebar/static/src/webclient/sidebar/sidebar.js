import { url } from '@web/core/utils/urls';
import { useService } from '@web/core/utils/hooks';
import { user } from "@web/core/user";

import { Component, onWillUnmount, useState } from '@odoo/owl';

export class SideBar extends Component {
	static template = 'imeco_web_sidebar.SideBar';
    static props = {};
	setup() {
        this.state = useState({ openSectionId: null });
        this.appMenuService = useService('app_menu');
        this.currentActionId = null;
    	if (user.activeCompany.has_sidebar_image) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'sidebar_image',
                id: user.activeCompany.id,
            });
    	}
    	const renderAfterMenuChange = () => {
            this.state.openSectionId = null;
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

    _onSectionClick(section) {
        if (!section) {
            return;
        }
        if (section.actionID) {
            this.currentActionId = section.actionID;
            this.state.openSectionId = null;
            this.render();
            this.appMenuService.selectApp(section);
        }
    }

    _onRootSectionClick(section) {
        if (!section) {
            this.state.openSectionId = null;
            return;
        }
        if (section.childrenTree && section.childrenTree.length) {
            if (this.state.openSectionId === section.id) {
                this.state.openSectionId = null;
            } else {
                this.state.openSectionId = section.id;
            }
            this.render();
            return;
        }
        this._onSectionClick(section);
    }
}
