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
import { mdiClockOutline, mdiHistory, mdiChartBar, mdiChartLine } from "@mdi/js";
import { ApexOptions } from 'apexcharts';

interface CategoryStats {
  name: string;
  timeUsed: number;
  timeLimit: number;
  lastActivity: string;
  topProcesses: Array<{ name: string; duration: number }>;
  peakHours: Array<{ hour: number; usage: number }>;
}

interface HourlyUsage {
  hour: number;
  usage: number;
  timestamp: string;
}

interface CategoryComparison {
  usage: Array<{ category: string; usage: number }>;
  limits: Array<{ category: string; limit: number }>;
}

interface TrendData {
  date: string;
  categories: Array<{ name: string; usage: number }>;
}

@customElement("twg-stats-card")
export class TWGStatsCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property() private config?: any;
  @property() private userId?: string;
  @state() private stats?: {
    dailyStats: CategoryStats[];
    weeklyStats: CategoryStats[];
    monthlyStats: CategoryStats[];
    peakHours: Array<{ hour: number; usage: number }>;
    hourlyUsage: HourlyUsage[];
    categoryComparison: CategoryComparison;
    trendAnalysis: TrendData[];
  };

  static get styles(): CSSResultGroup {
    return css`
      .card-content {
        padding: 16px;
      }
      .stats-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }
      .chart-container {
        height: 300px;
        margin: 16px 0;
      }
      .tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      .tab {
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
      }
      .tab.active {
        background: var(--primary-color);
        color: var(--text-primary-color);
      }
      .peak-hours {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 8px;
        margin: 16px 0;
      }
      .peak-hour-item {
        background: var(--card-background-color);
        padding: 8px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
      }
    `;
  }

  private getHourlyChartOptions(): ApexOptions {
    if (!this.stats) return {};

    return {
      chart: {
        type: 'area',
        height: 300,
      },
      series: [{
        name: 'Usage',
        data: this.stats.hourlyUsage.map(h => ({
          x: new Date(h.timestamp).getTime(),
          y: h.usage,
        })),
      }],
      xaxis: {
        type: 'datetime',
      },
      yaxis: {
        title: {
          text: 'Minutes',
        },
      },
      tooltip: {
        x: {
          format: 'HH:mm',
        },
      },
    };
  }

  private getCategoryComparisonOptions(): ApexOptions {
    if (!this.stats) return {};

    const { usage, limits } = this.stats.categoryComparison;
    return {
      chart: {
        type: 'bar',
        height: 300,
      },
      series: [
        {
          name: 'Usage',
          data: usage.map(u => u.usage),
        },
        {
          name: 'Limit',
          data: limits.map(l => l.limit),
        },
      ],
      xaxis: {
        categories: usage.map(u => u.category),
      },
      yaxis: {
        title: {
          text: 'Minutes',
        },
      },
    };
  }

  private getTrendChartOptions(): ApexOptions {
    if (!this.stats) return {};

    const categories = [...new Set(
      this.stats.trendAnalysis.flatMap(d => d.categories.map(c => c.name))
    )];

    return {
      chart: {
        type: 'line',
        height: 300,
      },
      series: categories.map(cat => ({
        name: cat,
        data: this.stats.trendAnalysis.map(d => {
          const catData = d.categories.find(c => c.name === cat);
          return {
            x: new Date(d.date).getTime(),
            y: catData ? catData.usage : 0,
          };
        }),
      })),
      xaxis: {
        type: 'datetime',
      },
      yaxis: {
        title: {
          text: 'Minutes',
        },
      },
    };
  }

  protected render() {
    if (!this.stats) {
      return html`<ha-card><div class="card-content">Loading...</div></ha-card>`;
    }

    return html`
      <ha-card>
        <div class="card-content">
          <div class="stats-header">
            <h2>Usage Statistics</h2>
            <ha-icon-button
              .path=${mdiHistory}
              @click=${this.loadStats}
              title="Refresh"
            ></ha-icon-button>
          </div>

          <div class="tabs">
            <div
              class="tab ${this.selectedView === 'overview' ? 'active' : ''}"
              @click=${() => this.selectView('overview')}
            >
              Overview
            </div>
            <div
              class="tab ${this.selectedView === 'hourly' ? 'active' : ''}"
              @click=${() => this.selectView('hourly')}
            >
              Hourly Usage
            </div>
            <div
              class="tab ${this.selectedView === 'comparison' ? 'active' : ''}"
              @click=${() => this.selectView('comparison')}
            >
              Category Comparison
            </div>
            <div
              class="tab ${this.selectedView === 'trends' ? 'active' : ''}"
              @click=${() => this.selectView('trends')}
            >
              Trends
            </div>
          </div>

          ${this.renderSelectedView()}
        </div>
      </ha-card>
    `;
  }

  private renderSelectedView() {
    switch (this.selectedView) {
      case 'overview':
        return this.renderOverview();
      case 'hourly':
        return this.renderHourlyUsage();
      case 'comparison':
        return this.renderCategoryComparison();
      case 'trends':
        return this.renderTrends();
      default:
        return html`Invalid view`;
    }
  }

  private renderOverview() {
    return html`
      <div class="peak-hours">
        <h3>Peak Usage Hours</h3>
        ${this.stats?.peakHours.map(
          peak => html`
            <div class="peak-hour-item">
              <div>${peak.hour}:00</div>
              <div>${this.formatDuration(peak.usage)}</div>
            </div>
          `
        )}
      </div>

      <div class="stats-grid">
        ${this.stats?.[`${this.selectedPeriod}Stats`].map(
          category => this.renderCategoryStats(category)
        )}
      </div>
    `;
  }

  private renderHourlyUsage() {
    return html`
      <div class="chart-container">
        <ha-chart-base
          .options=${this.getHourlyChartOptions()}
        ></ha-chart-base>
      </div>
    `;
  }

  private renderCategoryComparison() {
    return html`
      <div class="chart-container">
        <ha-chart-base
          .options=${this.getCategoryComparisonOptions()}
        ></ha-chart-base>
      </div>
    `;
  }

  private renderTrends() {
    return html`
      <div class="chart-container">
        <ha-chart-base
          .options=${this.getTrendChartOptions()}
        ></ha-chart-base>
      </div>
    `;
  }

  private renderCategoryStats(category: CategoryStats) {
    return html`
      <div class="category-stats">
        <h3>${category.name}</h3>
        <div class="progress-bar">
          <div
            class="progress-bar-fill"
            style="width: ${Math.min(
              (category.timeUsed / category.timeLimit) * 100,
              100
            )}%"
          ></div>
        </div>
        <div class="stat-item">
          <span>Time Used</span>
          <span>${this.formatDuration(category.timeUsed)}</span>
        </div>
        <div class="stat-item">
          <span>Time Limit</span>
          <span>${this.formatDuration(category.timeLimit)}</span>
        </div>
        <div class="stat-item">
          <span>Last Activity</span>
          <span>${formatDateTime(
            new Date(category.lastActivity),
            this.hass.locale
          )}</span>
        </div>

        <div class="top-processes">
          <h4>Top Processes</h4>
          ${category.topProcesses.map(
            process => html`
              <div class="process-item">
                <span>${process.name}</span>
                <span>${this.formatDuration(process.duration)}</span>
              </div>
            `
          )}
        </div>

        <div class="peak-hours">
          <h4>Peak Hours</h4>
          ${category.peakHours.map(
            peak => html`
              <div class="peak-hour-item">
                <div>${peak.hour}:00</div>
                <div>${this.formatDuration(peak.usage)}</div>
              </div>
            `
          )}
        </div>
      </div>
    `;
  }

  @state()
  private selectedPeriod: "daily" | "weekly" | "monthly" = "daily";

  @state()
  private selectedView: "overview" | "hourly" | "comparison" | "trends" = "overview";

  private selectPeriod(period: "daily" | "weekly" | "monthly"): void {
    this.selectedPeriod = period;
  }

  private selectView(view: "overview" | "hourly" | "comparison" | "trends"): void {
    this.selectedView = view;
  }

  private formatDuration(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return hours > 0
      ? `${hours}h ${remainingMinutes}m`
      : `${remainingMinutes}m`;
  }
} 