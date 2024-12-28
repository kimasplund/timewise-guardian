import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { HomeAssistant } from "custom-card-helpers";

@customElement("twg-config-card")
export class TWGConfigCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property() private config?: any;
  @property() private userId?: string;
  @property() private userConfig?: any;

  static get styles() {
    return css`
      .card-content {
        padding: 16px;
      }
      .section {
        margin-bottom: 16px;
      }
      .category {
        border: 1px solid var(--divider-color);
        padding: 16px;
        margin-bottom: 8px;
        border-radius: 4px;
      }
      mwc-button {
        margin-top: 8px;
      }
    `;
  }

  async firstUpdated() {
    if (this.userId) {
      await this.loadUserConfig();
    }
  }

  async loadUserConfig() {
    const response = await this.hass.callWS({
      type: "twg/config/get",
      user_id: this.userId,
    });
    this.userConfig = response;
  }

  async saveUserConfig() {
    await this.hass.callWS({
      type: "twg/config/update",
      user_id: this.userId,
      config: this.userConfig,
    });
  }

  render() {
    if (!this.userConfig) {
      return html`Loading...`;
    }

    return html`
      <ha-card>
        <div class="card-content">
          <div class="section">
            <h2>User Settings</h2>
            <ha-textfield
              label="User Name"
              .value=${this.userConfig.name}
              @change=${(e: any) => {
                this.userConfig = {
                  ...this.userConfig,
                  name: e.target.value,
                };
              }}
            ></ha-textfield>
          </div>

          <div class="section">
            <h2>Categories</h2>
            ${Object.entries(this.userConfig.categories).map(
              ([id, category]: [string, any]) => html`
                <div class="category">
                  <ha-textfield
                    label="Category Name"
                    .value=${category.name}
                    @change=${(e: any) => {
                      this.userConfig.categories[id] = {
                        ...category,
                        name: e.target.value,
                      };
                      this.requestUpdate();
                    }}
                  ></ha-textfield>

                  <ha-textfield
                    label="Time Limit (minutes)"
                    type="number"
                    .value=${category.time_limit}
                    @change=${(e: any) => {
                      this.userConfig.categories[id] = {
                        ...category,
                        time_limit: parseInt(e.target.value),
                      };
                      this.requestUpdate();
                    }}
                  ></ha-textfield>

                  <!-- Add more fields for processes, window titles, URLs -->
                </div>
              `
            )}
            <mwc-button @click=${this.addCategory}>Add Category</mwc-button>
          </div>

          <div class="section">
            <h2>Notifications</h2>
            <ha-switch
              .checked=${this.userConfig.notifications_enabled}
              @change=${(e: any) => {
                this.userConfig = {
                  ...this.userConfig,
                  notifications_enabled: e.target.checked,
                };
              }}
            >
              Enable Notifications
            </ha-switch>

            <ha-textfield
              label="Warning Threshold (%)"
              type="number"
              .value=${this.userConfig.warning_threshold}
              @change=${(e: any) => {
                this.userConfig = {
                  ...this.userConfig,
                  warning_threshold: parseInt(e.target.value),
                };
              }}
            ></ha-textfield>
          </div>

          <mwc-button @click=${this.saveUserConfig}>Save Changes</mwc-button>
        </div>
      </ha-card>
    `;
  }

  private addCategory() {
    const id = Math.random().toString(36).substr(2, 9);
    this.userConfig.categories[id] = {
      name: "New Category",
      processes: [],
      window_titles: [],
      urls: [],
      time_limit: 60,
      restrictions: [],
    };
    this.requestUpdate();
  }
} 