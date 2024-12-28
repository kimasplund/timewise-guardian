import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { HomeAssistant } from 'custom-card-helpers';
import { mdiAccountKey, mdiAccountGroup, mdiShieldKey, mdiPlus, mdiDelete, mdiPencil } from '@mdi/js';

interface Permission {
  name: string;
  description: string;
  source: string;
  source_name: string;
  granted_by?: string;
  expires_at?: string;
  reason?: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
}

interface Group {
  id: number;
  name: string;
  description: string;
  created_by_name: string;
}

@customElement('twg-permissions-card')
export class TWGPermissionsCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ type: Object }) public config: any = {};
  @property({ type: Number }) public userId?: number;
  @property({ type: Array }) private permissions: Permission[] = [];
  @property({ type: Array }) private roles: Role[] = [];
  @property({ type: Array }) private groups: Group[] = [];
  @property({ type: Boolean }) private isAdmin = false;
  @property({ type: Boolean }) private loading = true;

  static styles = css`
    :host {
      display: block;
      padding: 16px;
    }
    .section {
      margin-bottom: 24px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .permission-list {
      display: grid;
      gap: 8px;
    }
    .permission-item {
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: center;
      padding: 12px;
      border-radius: 8px;
      background: var(--card-background-color, #fff);
      box-shadow: var(--ha-card-box-shadow, none);
    }
    .permission-info {
      display: grid;
      gap: 4px;
    }
    .permission-name {
      font-weight: bold;
    }
    .permission-source {
      font-size: 0.9em;
      color: var(--secondary-text-color);
    }
    .permission-actions {
      display: flex;
      gap: 8px;
    }
    .role-section, .group-section {
      margin-top: 24px;
    }
    ha-button {
      --mdc-theme-primary: var(--primary-color);
    }
    .add-button {
      margin-top: 16px;
    }
  `;

  protected firstUpdated() {
    this.loadData();
  }

  private async loadData() {
    this.loading = true;
    try {
      // Load permissions
      const permissionsResponse = await this.hass.callWS({
        type: 'twg/get_user_permissions',
        user_id: this.userId,
      });
      this.permissions = permissionsResponse.permissions;

      // Load roles if admin
      if (this.isAdmin) {
        const rolesResponse = await this.hass.callWS({
          type: 'twg/get_roles',
        });
        this.roles = rolesResponse.roles;
      }

      // Load groups
      const groupsResponse = await this.hass.callWS({
        type: 'twg/get_user_groups',
        user_id: this.userId,
      });
      this.groups = groupsResponse.groups;

      // Check if user is admin
      const userResponse = await this.hass.callWS({
        type: 'twg/get_user',
        user_id: this.userId,
      });
      this.isAdmin = userResponse.user?.role_name === 'admin';
    } catch (error) {
      console.error('Error loading permissions data:', error);
    } finally {
      this.loading = false;
    }
  }

  private async handleGrantPermission() {
    const result = await this.hass.callWS({
      type: 'twg/grant_permission',
      user_id: this.userId,
      permission: 'view_statistics', // Example permission
      expires_at: null,
      reason: 'Granted via UI',
    });
    if (result.success) {
      this.loadData();
    }
  }

  private async handleRevokePermission(permission: string) {
    const result = await this.hass.callWS({
      type: 'twg/revoke_permission',
      user_id: this.userId,
      permission: permission,
    });
    if (result.success) {
      this.loadData();
    }
  }

  protected render() {
    if (this.loading) {
      return html`<ha-circular-progress active></ha-circular-progress>`;
    }

    return html`
      <div class="section">
        <div class="header">
          <h2>Permissions</h2>
          ${this.isAdmin ? html`
            <ha-button @click=${this.handleGrantPermission}>
              <ha-svg-icon path=${mdiPlus}></ha-svg-icon>
              Grant Permission
            </ha-button>
          ` : ''}
        </div>
        <div class="permission-list">
          ${this.permissions.map(perm => html`
            <div class="permission-item">
              <div class="permission-info">
                <div class="permission-name">${perm.name}</div>
                <div class="permission-description">${perm.description}</div>
                <div class="permission-source">
                  Via ${perm.source}: ${perm.source_name}
                  ${perm.expires_at ? html`(Expires: ${perm.expires_at})` : ''}
                </div>
              </div>
              ${this.isAdmin && perm.source === 'override' ? html`
                <div class="permission-actions">
                  <ha-icon-button
                    @click=${() => this.handleRevokePermission(perm.name)}
                    path=${mdiDelete}
                  ></ha-icon-button>
                </div>
              ` : ''}
            </div>
          `)}
        </div>
      </div>

      ${this.isAdmin ? html`
        <div class="role-section">
          <div class="header">
            <h2>Roles</h2>
            <ha-button>
              <ha-svg-icon path=${mdiPlus}></ha-svg-icon>
              Add Role
            </ha-button>
          </div>
          <div class="permission-list">
            ${this.roles.map(role => html`
              <div class="permission-item">
                <div class="permission-info">
                  <div class="permission-name">${role.name}</div>
                  <div class="permission-description">${role.description}</div>
                </div>
                <div class="permission-actions">
                  <ha-icon-button path=${mdiPencil}></ha-icon-button>
                  <ha-icon-button path=${mdiDelete}></ha-icon-button>
                </div>
              </div>
            `)}
          </div>
        </div>

        <div class="group-section">
          <div class="header">
            <h2>Groups</h2>
            <ha-button>
              <ha-svg-icon path=${mdiPlus}></ha-svg-icon>
              Create Group
            </ha-button>
          </div>
          <div class="permission-list">
            ${this.groups.map(group => html`
              <div class="permission-item">
                <div class="permission-info">
                  <div class="permission-name">${group.name}</div>
                  <div class="permission-description">${group.description}</div>
                  <div class="permission-source">Created by: ${group.created_by_name}</div>
                </div>
                <div class="permission-actions">
                  <ha-icon-button path=${mdiPencil}></ha-icon-button>
                  <ha-icon-button path=${mdiDelete}></ha-icon-button>
                </div>
              </div>
            `)}
          </div>
        </div>
      ` : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'twg-permissions-card': TWGPermissionsCard;
  }
} 