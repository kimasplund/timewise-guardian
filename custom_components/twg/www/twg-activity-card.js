class TWGActivityCard extends HTMLElement {
  set hass(hass) {
    if (!this.content) {
      this.innerHTML = `
        <ha-card>
          <style>
            .card-content {
              padding: 16px;
            }
            .activity-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 16px;
            }
            .activity-title {
              font-size: 1.2em;
              font-weight: 500;
            }
            .activity-time {
              font-size: 1.1em;
              color: var(--primary-text-color);
            }
            .activity-grid {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
              gap: 16px;
              margin-top: 16px;
            }
            .activity-item {
              background: var(--card-background-color);
              padding: 12px;
              border-radius: 8px;
              box-shadow: var(--ha-card-box-shadow, none);
            }
            .activity-item-header {
              display: flex;
              align-items: center;
              margin-bottom: 8px;
            }
            .activity-item-header ha-icon {
              margin-right: 8px;
            }
            .activity-item-title {
              font-weight: 500;
            }
            .activity-item-value {
              font-size: 1.1em;
              margin-top: 4px;
            }
            .activity-progress {
              width: 100%;
              height: 4px;
              background: var(--disabled-text-color);
              border-radius: 2px;
              margin-top: 8px;
            }
            .activity-progress-bar {
              height: 100%;
              border-radius: 2px;
              transition: width 0.3s ease;
            }
            .status-green {
              background: var(--success-color);
            }
            .status-yellow {
              background: var(--warning-color);
            }
            .status-red {
              background: var(--error-color);
            }
          </style>
          <div class="card-content">
            <div class="activity-header">
              <div class="activity-title">Activity Monitor</div>
              <div class="activity-time"></div>
            </div>
            <div class="activity-grid"></div>
          </div>
        </ha-card>
      `;
      this.content = this.querySelector('.card-content');
      this.grid = this.querySelector('.activity-grid');
      this.timeElement = this.querySelector('.activity-time');
    }

    const activityEntity = this.config.activity_entity || 'sensor.twg_activity';
    const timeEntity = this.config.time_entity || 'sensor.twg_time_remaining';
    
    const activity = hass.states[activityEntity];
    const timeRemaining = hass.states[timeEntity];

    if (!activity || !timeRemaining) {
      this.content.innerHTML = 'Entities not found.';
      return;
    }

    // Update time
    const now = new Date();
    this.timeElement.textContent = now.toLocaleTimeString();

    // Create activity items
    const categories = {
      games: {
        icon: 'mdi:gamepad-variant',
        title: 'Games',
        used: timeRemaining.attributes.total_used_today || 0,
        limit: timeRemaining.attributes.daily_limit || 120
      },
      entertainment: {
        icon: 'mdi:youtube',
        title: 'Entertainment',
        used: timeRemaining.attributes.total_used_today || 0,
        limit: timeRemaining.attributes.daily_limit || 180
      }
    };

    this.grid.innerHTML = Object.entries(categories)
      .map(([key, cat]) => {
        const percentage = (cat.used / cat.limit) * 100;
        let statusClass = 'status-green';
        if (percentage >= 100) statusClass = 'status-red';
        else if (percentage >= 80) statusClass = 'status-yellow';

        return `
          <div class="activity-item">
            <div class="activity-item-header">
              <ha-icon icon="${cat.icon}"></ha-icon>
              <span class="activity-item-title">${cat.title}</span>
            </div>
            <div class="activity-item-value">
              ${cat.used} / ${cat.limit} min
            </div>
            <div class="activity-progress">
              <div class="activity-progress-bar ${statusClass}"
                   style="width: ${Math.min(percentage, 100)}%">
              </div>
            </div>
          </div>
        `;
      })
      .join('');

    // Add current activity
    this.grid.innerHTML += `
      <div class="activity-item">
        <div class="activity-item-header">
          <ha-icon icon="mdi:monitor"></ha-icon>
          <span class="activity-item-title">Current Activity</span>
        </div>
        <div class="activity-item-value">
          ${activity.state}
        </div>
      </div>
    `;
  }

  setConfig(config) {
    if (!config.activity_entity && !config.time_entity) {
      throw new Error('Please define activity_entity and time_entity');
    }
    this.config = config;
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {
      activity_entity: 'sensor.twg_activity',
      time_entity: 'sensor.twg_time_remaining'
    };
  }
}

customElements.define('twg-activity-card', TWGActivityCard); 