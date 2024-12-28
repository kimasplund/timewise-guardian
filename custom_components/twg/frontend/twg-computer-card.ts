import {
  LitElement,
  html,
  css,
  PropertyValues,
  CSSResultGroup,
} from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  HomeAssistant,
  formatNumber,
  formatDateTime,
} from "custom-card-helpers";
import {
  mdiDesktopTower,
  mdiNetwork,
  mdiClock,
  mdiAccount,
  mdiChartLine,
} from "@mdi/js";
import { ApexOptions } from 'apexcharts';

interface ComputerStats {
  computerInfo: {
    id: string;
    name: string;
    os: string;
    lastSeen: string;
  };
  uptime: {
    total: number;
    current: number;
    lastBoot: string;
  };
  networkStats: {
    daily: Array<{
      date: string;
      download: number;
      upload: number;
    }>;
    total: {
      download: number;
      upload: number;
    };
  };
  userSessions: Array<{
    user: string;
    start: string;
    end: string;
    activities: any[];
  }>;
  resourceUsage: {
    cpu: Array<{ timestamp: string; value: number }>;
    memory: Array<{ timestamp: string; value: number }>;
    disk: Array<{ timestamp: string; value: number }>;
  };
}

@customElement("twg-computer-card")
export class TWGComputerCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property() private config?: any;
  @property() private computerId?: string;
  @state() private stats?: ComputerStats;
  @state() private selectedSession?: string;

  static get styles(): CSSResultGroup {
    return css`
      .card-content {
        padding: 16px;
      }
      .computer-header {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
      }
      .computer-info {
        margin-left: 16px;
      }
      .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 16px;
      }
      .stat-card {
        background: var(--card-background-color);
        border-radius: 8px;
        padding: 16px;
        border: 1px solid var(--divider-color);
      }
      .chart-container {
        height: 200px;
        margin: 16px 0;
      }
      .sessions-list {
        margin-top: 16px;
      }
      .session-item {
        display: flex;
        justify-content: space-between;
        padding: 8px;
        border-radius: 4px;
        cursor: pointer;
        margin: 4px 0;
      }
      .session-item:hover {
        background: var(--primary-color);
        color: var(--text-primary-color);
      }
      .resource-charts {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 16px;
      }
    `;
  }

  protected firstUpdated(): void {
    this.loadStats();
  }

  private async loadStats(): Promise<void> {
    if (!this.computerId) return;

    const stats = await this.hass.callWS({
      type: "twg/stats/get",
      computer_id: this.computerId,
    });

    this.stats = stats;
  }

  private getNetworkChartOptions(): ApexOptions {
    if (!this.stats) return {};

    return {
      chart: {
        type: 'area',
        height: 200,
        stacked: true,
      },
      series: [
        {
          name: 'Download',
          data: this.stats.networkStats.daily.map(d => ({
            x: new Date(d.date).getTime(),
            y: d.download,
          })),
        },
        {
          name: 'Upload',
          data: this.stats.networkStats.daily.map(d => ({
            x: new Date(d.date).getTime(),
            y: d.upload,
          })),
        },
      ],
      xaxis: {
        type: 'datetime',
      },
      yaxis: {
        title: {
          text: 'MB',
        },
      },
    };
  }

  private getResourceChartOptions(data: Array<{ timestamp: string; value: number }>, title: string): ApexOptions {
    return {
      chart: {
        type: 'line',
        height: 200,
      },
      series: [
        {
          name: title,
          data: data.map(d => ({
            x: new Date(d.timestamp).getTime(),
            y: d.value,
          })),
        },
      ],
      xaxis: {
        type: 'datetime',
      },
      yaxis: {
        title: {
          text: '%',
        },
        max: 100,
      },
    };
  }

  private async viewSession(sessionId: string): Promise<void> {
    this.selectedSession = sessionId;
    const event = new CustomEvent('view-session', {
      detail: { sessionId },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  protected render() {
    if (!this.stats) {
      return html`<ha-card><div class="card-content">Loading...</div></ha-card>`;
    }

    const { computerInfo, uptime, networkStats, userSessions, resourceUsage } = this.stats;

    return html`
      <ha-card>
        <div class="card-content">
          <div class="computer-header">
            <ha-icon-button
              .path=${mdiDesktopTower}
              title="Computer"
            ></ha-icon-button>
            <div class="computer-info">
              <h2>${computerInfo.name}</h2>
              <div>${computerInfo.os}</div>
              <div>Last seen: ${formatDateTime(new Date(computerInfo.lastSeen), this.hass.locale)}</div>
            </div>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <h3>Uptime</h3>
              <div>Current: ${Math.floor(uptime.current)}h</div>
              <div>Total: ${Math.floor(uptime.total)}h</div>
              <div>Last boot: ${formatDateTime(new Date(uptime.lastBoot), this.hass.locale)}</div>
            </div>

            <div class="stat-card">
              <h3>Network Usage</h3>
              <div>Download: ${networkStats.total.download.toFixed(2)} MB</div>
              <div>Upload: ${networkStats.total.upload.toFixed(2)} MB</div>
            </div>
          </div>

          <div class="chart-container">
            <h3>Network History</h3>
            <ha-chart-base
              .options=${this.getNetworkChartOptions()}
            ></ha-chart-base>
          </div>

          <div class="resource-charts">
            <div class="chart-container">
              <h3>CPU Usage</h3>
              <ha-chart-base
                .options=${this.getResourceChartOptions(resourceUsage.cpu, 'CPU')}
              ></ha-chart-base>
            </div>

            <div class="chart-container">
              <h3>Memory Usage</h3>
              <ha-chart-base
                .options=${this.getResourceChartOptions(resourceUsage.memory, 'Memory')}
              ></ha-chart-base>
            </div>

            <div class="chart-container">
              <h3>Disk Usage</h3>
              <ha-chart-base
                .options=${this.getResourceChartOptions(resourceUsage.disk, 'Disk')}
              ></ha-chart-base>
            </div>
          </div>

          <div class="sessions-list">
            <h3>User Sessions</h3>
            ${userSessions.map(session => html`
              <div
                class="session-item"
                @click=${() => this.viewSession(session.user)}
              >
                <div>${session.user}</div>
                <div>${formatDateTime(new Date(session.start), this.hass.locale)}</div>
                <div>${session.end ? formatDateTime(new Date(session.end), this.hass.locale) : 'Active'}</div>
              </div>
            `)}
          </div>
        </div>
      </ha-card>
    `;
  }
} 