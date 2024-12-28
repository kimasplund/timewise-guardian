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
  formatDuration,
} from "custom-card-helpers";
import {
  mdiAccount,
  mdiDesktopTower,
  mdiClock,
  mdiNetwork,
  mdiChartLine,
} from "@mdi/js";
import { ApexOptions } from 'apexcharts';

interface SessionStats {
  sessionInfo: {
    id: string;
    user: string;
    computer: string;
    startTime: string;
    endTime: string | null;
    duration: number;
  };
  activities: {
    timeline: Array<{
      activity: string;
      start: string;
      category: string;
      process: string;
      duration: number;
      details: {
        window_title: string;
        url: string;
        domain: string;
      };
    }>;
    summaries: {
      activities: Array<{ name: string; duration: number }>;
      processes: Array<{ name: string; duration: number }>;
      categories: Array<{ name: string; duration: number }>;
    };
    heatmap: Array<{
      hour: number;
      categories: Array<{ category: string; duration: number }>;
    }>;
  };
  resourceUsage: {
    cpu: {
      history: Array<{ timestamp: string; value: number; per_core: number[] }>;
      average: number;
      peak: number;
      per_core_avg: number[];
    };
    memory: {
      history: Array<{ timestamp: string; value: number; virtual: number; swap: number }>;
      average: number;
      peak: number;
      swap_avg: number;
    };
    gpu?: {
      history: Array<{ timestamp: string; usage: number; memory: number; temperature: number }>;
      average: number;
      peak: number;
      memory_avg: number;
    };
  };
  networkUsage: {
    download: number;
    upload: number;
    history: Array<{
      timestamp: string;
      download: number;
      upload: number;
    }>;
  };
}

@customElement("twg-session-card")
export class TWGSessionCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property() private config?: any;
  @property() private sessionId?: string;
  @state() private stats?: SessionStats;

  static get styles(): CSSResultGroup {
    return css`
      .card-content {
        padding: 16px;
      }
      .session-header {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
      }
      .session-info {
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
      .activities-list {
        margin-top: 16px;
      }
      .activity-item {
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: 16px;
        padding: 8px;
        border-radius: 4px;
        margin: 4px 0;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
      }
      .category-tag {
        padding: 2px 8px;
        border-radius: 12px;
        background: var(--primary-color);
        color: var(--text-primary-color);
        font-size: 0.9em;
      }
      .chart-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 16px;
        margin: 16px 0;
      }
      .heatmap-container {
        margin: 16px 0;
        height: 250px;
      }
    `;
  }

  protected firstUpdated(): void {
    this.loadStats();
  }

  private async loadStats(): Promise<void> {
    if (!this.sessionId) return;

    const stats = await this.hass.callWS({
      type: "twg/stats/get",
      session_id: this.sessionId,
    });

    this.stats = stats;
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
          data: this.stats.networkUsage.history.map(d => ({
            x: new Date(d.timestamp).getTime(),
            y: d.download,
          })),
        },
        {
          name: 'Upload',
          data: this.stats.networkUsage.history.map(d => ({
            x: new Date(d.timestamp).getTime(),
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

  private getPieChartOptions(data: Array<{ name: string; duration: number }>, title: string): ApexOptions {
    return {
      chart: {
        type: 'pie',
        height: 300,
      },
      series: data.map(d => d.duration),
      labels: data.map(d => d.name),
      title: {
        text: title,
        align: 'center',
      },
      legend: {
        position: 'bottom',
      },
      tooltip: {
        y: {
          formatter: (value) => `${Math.round(value)}m`,
        },
      },
    };
  }

  private getHeatmapOptions(): ApexOptions {
    if (!this.stats) return {};

    const categories = Array.from(
      new Set(
        this.stats.activities.heatmap
          .flatMap(h => h.categories.map(c => c.category))
      )
    );

    const data = categories.map(category => ({
      name: category,
      data: this.stats!.activities.heatmap.map(hour => {
        const cat = hour.categories.find(c => c.category === category);
        return {
          x: hour.hour,
          y: cat ? cat.duration : 0,
        };
      }),
    }));

    return {
      chart: {
        type: 'heatmap',
        height: 250,
      },
      series: data,
      dataLabels: {
        enabled: false,
      },
      colors: ["#008FFB"],
      title: {
        text: 'Activity Heatmap',
        align: 'center',
      },
      xaxis: {
        type: 'category',
        categories: Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0')),
      },
    };
  }

  protected render() {
    if (!this.stats) {
      return html`<ha-card><div class="card-content">Loading...</div></ha-card>`;
    }

    const { sessionInfo, activities, resourceUsage, networkUsage } = this.stats;

    return html`
      <ha-card>
        <div class="card-content">
          <div class="session-header">
            <ha-icon-button
              .path=${mdiAccount}
              title="User Session"
            ></ha-icon-button>
            <div class="session-info">
              <h2>${sessionInfo.user}</h2>
              <div>Computer: ${sessionInfo.computer}</div>
              <div>
                ${formatDateTime(new Date(sessionInfo.startTime), this.hass.locale)}
                ${sessionInfo.endTime ? html`
                  - ${formatDateTime(new Date(sessionInfo.endTime), this.hass.locale)}
                ` : html`(Active)`}
              </div>
              <div>Duration: ${Math.floor(sessionInfo.duration)}h ${Math.round((sessionInfo.duration % 1) * 60)}m</div>
            </div>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <h3>Network Usage</h3>
              <div>Download: ${networkUsage.download.toFixed(2)} MB</div>
              <div>Upload: ${networkUsage.upload.toFixed(2)} MB</div>
            </div>

            <div class="stat-card">
              <h3>Resource Usage</h3>
              <div>CPU Avg: ${resourceUsage.cpu.average}%</div>
              <div>CPU Peak: ${resourceUsage.cpu.peak}%</div>
              <div>Memory Avg: ${resourceUsage.memory.average}%</div>
              <div>Memory Peak: ${resourceUsage.memory.peak}%</div>
              ${resourceUsage.gpu ? html`
                <div>GPU Avg: ${resourceUsage.gpu.average}%</div>
                <div>GPU Peak: ${resourceUsage.gpu.peak}%</div>
              ` : ''}
            </div>
          </div>

          <div class="chart-grid">
            <div class="chart-container">
              <ha-chart-base
                .options=${this.getPieChartOptions(activities.summaries.categories, 'Category Distribution')}
              ></ha-chart-base>
            </div>

            <div class="chart-container">
              <ha-chart-base
                .options=${this.getPieChartOptions(activities.summaries.processes, 'Process Distribution')}
              ></ha-chart-base>
            </div>
          </div>

          <div class="heatmap-container">
            <ha-chart-base
              .options=${this.getHeatmapOptions()}
            ></ha-chart-base>
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
                .options=${this.getResourceChartOptions(resourceUsage.cpu.history, 'CPU')}
              ></ha-chart-base>
            </div>

            <div class="chart-container">
              <h3>Memory Usage</h3>
              <ha-chart-base
                .options=${this.getResourceChartOptions(resourceUsage.memory.history, 'Memory')}
              ></ha-chart-base>
            </div>

            ${resourceUsage.gpu ? html`
              <div class="chart-container">
                <h3>GPU Usage</h3>
                <ha-chart-base
                  .options=${this.getResourceChartOptions(
                    resourceUsage.gpu.history.map(h => ({
                      timestamp: h.timestamp,
                      value: h.usage,
                    })),
                    'GPU'
                  )}
                ></ha-chart-base>
              </div>
            ` : ''}
          </div>

          <div class="activities-list">
            <h3>Activities</h3>
            ${activities.timeline.map(activity => html`
              <div class="activity-item">
                <div>${formatDateTime(new Date(activity.start), this.hass.locale)}</div>
                <div>
                  ${activity.process}
                  <span class="category-tag">${activity.category}</span>
                </div>
                <div>${activity.activity}</div>
              </div>
            `)}
          </div>
        </div>
      </ha-card>
    `;
  }
} 