import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { HomeAssistant } from 'custom-card-helpers';
import { mdiHistory, mdiAccountKey, mdiAccountGroup, mdiFilter } from '@mdi/js';

interface AuditLog {
  id: number;
  action_type: string;
  created_at: string;
  performed_by_name: string;
  details?: string;
  reason?: string;
}

interface PermissionAuditLog extends AuditLog {
  user_name: string;
  target_type: string;
  target_id: number;
  permission_name: string;
}

interface RoleAuditLog extends AuditLog {
  role_name: string;
}

interface GroupAuditLog extends AuditLog {
  group_name: string;
}

@customElement('twg-audit-card')
export class TWGAuditCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ type: Object }) public config: any = {};
  @property({ type: Array }) private permissionLogs: PermissionAuditLog[] = [];
  @property({ type: Array }) private roleLogs: RoleAuditLog[] = [];
  @property({ type: Array }) private groupLogs: GroupAuditLog[] = [];
  @property({ type: String }) private selectedTab = 'permissions';
  @property({ type: Boolean }) private loading = true;
  @property({ type: Object }) private filters = {
    userId: null as number | null,
    targetType: null as string | null,
    roleId: null as number | null,
    groupId: null as number | null,
  };

  static styles = css`
    :host {
      display: block;
      padding: 16px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .tabs {
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
    }
    .tab {
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, #e0e0e0);
    }
    .tab.active {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }
    .filters {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }
    .log-list {
      display: grid;
      gap: 8px;
    }
    .log-item {
      display: grid;
      gap: 8px;
      padding: 12px;
      border-radius: 8px;
      background: var(--card-background-color, #fff);
      box-shadow: var(--ha-card-box-shadow, none);
    }
    .log-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .log-title {
      font-weight: bold;
    }
    .log-timestamp {
      font-size: 0.9em;
      color: var(--secondary-text-color);
    }
    .log-details {
      color: var(--primary-text-color);
    }
    .log-meta {
      font-size: 0.9em;
      color: var(--secondary-text-color);
    }
  `;

  protected firstUpdated() {
    this.loadData();
  }

  private async loadData() {
    this.loading = true;
    try {
      const [permissionLogs, roleLogs, groupLogs] = await Promise.all([
        this.hass.callWS({
          type: 'twg/get_permission_audit_logs',
          user_id: this.filters.userId,
          target_type: this.filters.targetType,
        }),
        this.hass.callWS({
          type: 'twg/get_role_audit_logs',
          role_id: this.filters.roleId,
        }),
        this.hass.callWS({
          type: 'twg/get_group_audit_logs',
          group_id: this.filters.groupId,
        }),
      ]);

      this.permissionLogs = permissionLogs.logs;
      this.roleLogs = roleLogs.logs;
      this.groupLogs = groupLogs.logs;
    } catch (error) {
      console.error('Error loading audit logs:', error);
    } finally {
      this.loading = false;
    }
  }

  private handleTabChange(tab: string) {
    this.selectedTab = tab;
  }

  private handleFilterChange(filterType: string, value: any) {
    this.filters = {
      ...this.filters,
      [filterType]: value,
    };
    this.loadData();
  }

  private formatTimestamp(timestamp: string): string {
    return new Date(timestamp).toLocaleString();
  }

  private renderPermissionLog(log: PermissionAuditLog) {
    return html`
      <div class="log-item">
        <div class="log-header">
          <div class="log-title">
            ${log.action_type.toUpperCase()}: ${log.permission_name}
          </div>
          <div class="log-timestamp">${this.formatTimestamp(log.created_at)}</div>
        </div>
        <div class="log-details">
          User: ${log.user_name}
          Target: ${log.target_type} (${log.target_id})
        </div>
        <div class="log-meta">
          Performed by: ${log.performed_by_name}
          ${log.reason ? html`<br>Reason: ${log.reason}` : ''}
        </div>
      </div>
    `;
  }

  private renderRoleLog(log: RoleAuditLog) {
    return html`
      <div class="log-item">
        <div class="log-header">
          <div class="log-title">
            ${log.action_type.toUpperCase()}: ${log.role_name}
          </div>
          <div class="log-timestamp">${this.formatTimestamp(log.created_at)}</div>
        </div>
        <div class="log-details">
          ${log.details ? JSON.parse(log.details).join(', ') : ''}
        </div>
        <div class="log-meta">
          Performed by: ${log.performed_by_name}
          ${log.reason ? html`<br>Reason: ${log.reason}` : ''}
        </div>
      </div>
    `;
  }

  private renderGroupLog(log: GroupAuditLog) {
    return html`
      <div class="log-item">
        <div class="log-header">
          <div class="log-title">
            ${log.action_type.toUpperCase()}: ${log.group_name}
          </div>
          <div class="log-timestamp">${this.formatTimestamp(log.created_at)}</div>
        </div>
        <div class="log-details">
          ${log.details ? JSON.parse(log.details).join(', ') : ''}
        </div>
        <div class="log-meta">
          Performed by: ${log.performed_by_name}
          ${log.reason ? html`<br>Reason: ${log.reason}` : ''}
        </div>
      </div>
    `;
  }

  protected render() {
    if (this.loading) {
      return html`<ha-circular-progress active></ha-circular-progress>`;
    }

    return html`
      <div class="header">
        <h2>Audit Logs</h2>
        <ha-button @click=${() => this.loadData()}>
          <ha-svg-icon path=${mdiHistory}></ha-svg-icon>
          Refresh
        </ha-button>
      </div>

      <div class="tabs">
        <div
          class="tab ${this.selectedTab === 'permissions' ? 'active' : ''}"
          @click=${() => this.handleTabChange('permissions')}
        >
          <ha-svg-icon path=${mdiAccountKey}></ha-svg-icon>
          Permissions
        </div>
        <div
          class="tab ${this.selectedTab === 'roles' ? 'active' : ''}"
          @click=${() => this.handleTabChange('roles')}
        >
          <ha-svg-icon path=${mdiAccountKey}></ha-svg-icon>
          Roles
        </div>
        <div
          class="tab ${this.selectedTab === 'groups' ? 'active' : ''}"
          @click=${() => this.handleTabChange('groups')}
        >
          <ha-svg-icon path=${mdiAccountGroup}></ha-svg-icon>
          Groups
        </div>
      </div>

      <div class="filters">
        ${this.selectedTab === 'permissions' ? html`
          <ha-select
            label="Filter by User"
            .value=${this.filters.userId}
            @selected=${(e: CustomEvent) =>
              this.handleFilterChange('userId', e.detail.value)}
          >
            <ha-list-item value="">All Users</ha-list-item>
            <!-- Add user options dynamically -->
          </ha-select>

          <ha-select
            label="Filter by Target Type"
            .value=${this.filters.targetType}
            @selected=${(e: CustomEvent) =>
              this.handleFilterChange('targetType', e.detail.value)}
          >
            <ha-list-item value="">All Types</ha-list-item>
            <ha-list-item value="user">User</ha-list-item>
            <ha-list-item value="role">Role</ha-list-item>
            <ha-list-item value="group">Group</ha-list-item>
          </ha-select>
        ` : ''}

        ${this.selectedTab === 'roles' ? html`
          <ha-select
            label="Filter by Role"
            .value=${this.filters.roleId}
            @selected=${(e: CustomEvent) =>
              this.handleFilterChange('roleId', e.detail.value)}
          >
            <ha-list-item value="">All Roles</ha-list-item>
            <!-- Add role options dynamically -->
          </ha-select>
        ` : ''}

        ${this.selectedTab === 'groups' ? html`
          <ha-select
            label="Filter by Group"
            .value=${this.filters.groupId}
            @selected=${(e: CustomEvent) =>
              this.handleFilterChange('groupId', e.detail.value)}
          >
            <ha-list-item value="">All Groups</ha-list-item>
            <!-- Add group options dynamically -->
          </ha-select>
        ` : ''}
      </div>

      <div class="log-list">
        ${this.selectedTab === 'permissions'
          ? this.permissionLogs.map(log => this.renderPermissionLog(log))
          : this.selectedTab === 'roles'
          ? this.roleLogs.map(log => this.renderRoleLog(log))
          : this.groupLogs.map(log => this.renderGroupLog(log))}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'twg-audit-card': TWGAuditCard;
  }
} 