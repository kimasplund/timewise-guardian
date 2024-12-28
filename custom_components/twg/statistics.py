"""Statistics handler for Timewise Guardian."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from homeassistant.core import HomeAssistant, callback
from homeassistant.components.websocket_api import (
    websocket_command,
    ActiveConnection,
)
from homeassistant.components.recorder import history
import voluptuous as vol

from .const import DOMAIN
from .models import TWGStore

# Main websocket command handler
@callback
@websocket_command({
    vol.Required("type"): "twg/stats/get",
    vol.Required("user_id"): str,
    vol.Optional("computer_id"): str,
    vol.Optional("session_id"): str,
})
async def websocket_get_stats(hass: HomeAssistant, connection: ActiveConnection, msg: dict) -> None:
    """Handle get stats command."""
    try:
        store = hass.data[DOMAIN][msg["entry_id"]]
        
        if "session_id" in msg:
            stats = await get_session_stats(hass, store, msg["session_id"])
        elif "computer_id" in msg:
            stats = await get_computer_stats(hass, store, msg["computer_id"])
        else:
            stats = await get_user_stats(hass, store, msg["user_id"])
        
        connection.send_result(msg["id"], stats)
    except KeyError as err:
        connection.send_error(msg["id"], "invalid_entry", f"Entry not found: {err}")
    except Exception as err:
        connection.send_error(msg["id"], "stats_error", str(err))

# Main statistics functions
async def get_user_stats(hass: HomeAssistant, store: TWGStore, user_id: str) -> dict:
    """Get statistics for a user."""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # Get user's activity history from recorder
    activity_history = await get_activity_history(hass, store, user_id, month_start)

    # Calculate statistics for different time periods
    daily_stats = calculate_period_stats(activity_history, today, now)
    weekly_stats = calculate_period_stats(activity_history, week_start, now)
    monthly_stats = calculate_period_stats(activity_history, month_start, now)

    # Calculate additional analytics
    peak_hours = calculate_peak_hours(activity_history)
    hourly_usage = calculate_hourly_usage(activity_history)
    category_comparison = calculate_category_comparison(activity_history)
    trend_analysis = calculate_trend_analysis(activity_history, week_start)

    return {
        "dailyStats": daily_stats,
        "weeklyStats": weekly_stats,
        "monthlyStats": monthly_stats,
        "peakHours": peak_hours,
        "hourlyUsage": hourly_usage,
        "categoryComparison": category_comparison,
        "trendAnalysis": trend_analysis,
    }

async def get_computer_stats(hass: HomeAssistant, store: TWGStore, computer_id: str) -> dict:
    """Get statistics for a specific computer."""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())

    # Get computer's activity history
    activity_history = await get_activity_history(hass, store, computer_id, week_start)

    # Calculate system metrics
    uptime = calculate_uptime(activity_history)
    network_stats = calculate_network_stats(activity_history)
    user_sessions = calculate_user_sessions(activity_history)
    resource_usage = calculate_resource_usage(activity_history)

    return {
        "computerInfo": {
            "id": computer_id,
            "name": activity_history[0].attributes.get("computer_name", computer_id) if activity_history else computer_id,
            "os": activity_history[0].attributes.get("os_info", "Unknown") if activity_history else "Unknown",
            "lastSeen": activity_history[-1].last_updated.isoformat() if activity_history else None,
        },
        "uptime": uptime,
        "networkStats": network_stats,
        "userSessions": user_sessions,
        "resourceUsage": resource_usage,
    }

async def get_session_stats(hass: HomeAssistant, store: TWGStore, session_id: str) -> dict:
    """Get statistics for a specific user session."""
    session = await get_session_history(hass, store, session_id)
    
    if not session:
        return {"error": "Session not found"}

    return {
        "sessionInfo": {
            "id": session_id,
            "user": session[0].attributes.get("user_name"),
            "computer": session[0].attributes.get("computer_name"),
            "startTime": session[0].last_updated.isoformat(),
            "endTime": session[-1].last_updated.isoformat() if len(session) > 1 else None,
            "duration": calculate_session_duration(session),
        },
        "activities": calculate_session_activities(session),
        "resourceUsage": calculate_session_resources(session),
        "networkUsage": calculate_session_network(session),
    }

# History retrieval functions
async def get_activity_history(
    hass: HomeAssistant,
    store: TWGStore,
    identifier: str,
    start_time: datetime
) -> List[dict]:
    """Get activity history from the recorder."""
    config = store.get_user_config(identifier)
    if config:
        # If identifier is a user_id
        entity_id = f"sensor.twg_user_{identifier}_activity"
    else:
        # If identifier is a computer_id
        entity_id = f"sensor.twg_computer_{identifier}_activity"

    states = await history.get_state_changes(
        hass,
        start_time,
        entity_id=entity_id,
        no_attributes=False,
        include_start_time_state=True
    )
    
    return states.get(entity_id, [])

async def get_session_history(
    hass: HomeAssistant,
    store: TWGStore,
    session_id: str
) -> List[dict]:
    """Get history for a specific session."""
    entity_id = f"sensor.twg_session_{session_id}"
    states = await history.get_state_changes(
        hass,
        None,
        entity_id=entity_id,
        no_attributes=False,
        include_start_time_state=True
    )
    return states.get(entity_id, [])

def calculate_uptime(history: List[dict]) -> dict:
    """Calculate computer uptime statistics."""
    total_uptime = 0
    current_uptime = 0
    last_boot = None

    for state in history:
        if state.attributes.get("state") == "on":
            if not last_boot:
                last_boot = state.last_updated
        elif last_boot:
            duration = (state.last_updated - last_boot).total_seconds() / 3600  # hours
            total_uptime += duration
            if state == history[-1]:
                current_uptime = duration
            last_boot = None

    return {
        "total": round(total_uptime, 2),
        "current": round(current_uptime, 2),
        "lastBoot": last_boot.isoformat() if last_boot else None,
    }

def calculate_network_stats(history: List[dict]) -> dict:
    """Calculate network usage statistics."""
    download = defaultdict(float)
    upload = defaultdict(float)
    
    for state in history:
        day = state.last_updated.date()
        download[day] += state.attributes.get("network_download", 0)
        upload[day] += state.attributes.get("network_upload", 0)

    return {
        "daily": [
            {
                "date": day.isoformat(),
                "download": round(down / (1024 * 1024), 2),  # Convert to MB
                "upload": round(up / (1024 * 1024), 2),
            }
            for day, down, up in zip(download.keys(), download.values(), upload.values())
        ],
        "total": {
            "download": round(sum(download.values()) / (1024 * 1024), 2),
            "upload": round(sum(upload.values()) / (1024 * 1024), 2),
        },
    }

def calculate_user_sessions(history: List[dict]) -> List[dict]:
    """Calculate user session information."""
    sessions = []
    current_session = None

    for state in history:
        user = state.attributes.get("user_name")
        if user and not current_session:
            current_session = {
                "user": user,
                "start": state.last_updated.isoformat(),
                "activities": [],
            }
        elif not user and current_session:
            current_session["end"] = state.last_updated.isoformat()
            sessions.append(current_session)
            current_session = None

    if current_session:
        current_session["end"] = datetime.now().isoformat()
        sessions.append(current_session)

    return sessions

def calculate_resource_usage(history: List[dict]) -> dict:
    """Calculate system resource usage."""
    cpu_usage = []
    memory_usage = []
    disk_usage = []
    gpu_usage = []  # New GPU metrics
    network_interfaces = defaultdict(list)  # Per-interface stats
    temperatures = defaultdict(list)  # Temperature sensors
    processes = defaultdict(lambda: {
        "cpu": 0,
        "memory": 0,
        "io_read": 0,
        "io_write": 0,
        "network": 0,
    })

    for state in history:
        timestamp = state.last_updated.isoformat()
        attrs = state.attributes

        # Basic metrics
        cpu_usage.append({
            "timestamp": timestamp,
            "value": attrs.get("cpu_percent", 0),
            "per_core": attrs.get("cpu_per_core", []),
        })
        memory_usage.append({
            "timestamp": timestamp,
            "value": attrs.get("memory_percent", 0),
            "virtual": attrs.get("virtual_memory", 0),
            "swap": attrs.get("swap_memory", 0),
        })
        disk_usage.append({
            "timestamp": timestamp,
            "value": attrs.get("disk_percent", 0),
            "read_bytes": attrs.get("disk_read", 0),
            "write_bytes": attrs.get("disk_write", 0),
            "per_disk": attrs.get("disk_per_device", {}),
        })

        # GPU metrics
        if "gpu_percent" in attrs:
            gpu_usage.append({
                "timestamp": timestamp,
                "usage": attrs.get("gpu_percent", 0),
                "memory": attrs.get("gpu_memory", 0),
                "temperature": attrs.get("gpu_temp", 0),
            })

        # Network interface details
        for iface, stats in attrs.get("network_interfaces", {}).items():
            network_interfaces[iface].append({
                "timestamp": timestamp,
                "download": stats.get("bytes_recv", 0),
                "upload": stats.get("bytes_sent", 0),
                "packets_recv": stats.get("packets_recv", 0),
                "packets_sent": stats.get("packets_sent", 0),
                "errors": stats.get("errors", 0),
                "drops": stats.get("drops", 0),
            })

        # Temperature sensors
        for sensor, temp in attrs.get("temperatures", {}).items():
            temperatures[sensor].append({
                "timestamp": timestamp,
                "value": temp,
            })

        # Process details
        for proc in attrs.get("processes", []):
            processes[proc["name"]].update({
                "cpu": processes[proc["name"]]["cpu"] + proc.get("cpu_percent", 0),
                "memory": processes[proc["name"]]["memory"] + proc.get("memory_percent", 0),
                "io_read": processes[proc["name"]]["io_read"] + proc.get("io_read_bytes", 0),
                "io_write": processes[proc["name"]]["io_write"] + proc.get("io_write_bytes", 0),
                "network": processes[proc["name"]]["network"] + proc.get("network_bytes", 0),
            })

    # Process the data for visualization
    process_stats = {
        name: {
            "cpu": round(stats["cpu"] / len(history), 2),
            "memory": round(stats["memory"] / len(history), 2),
            "io_read": round(stats["io_read"] / (1024 * 1024), 2),  # MB
            "io_write": round(stats["io_write"] / (1024 * 1024), 2),  # MB
            "network": round(stats["network"] / (1024 * 1024), 2),  # MB
        }
        for name, stats in processes.items()
    }

    return {
        "cpu": {
            "history": cpu_usage[-100:],
            "average": round(sum(c["value"] for c in cpu_usage) / len(cpu_usage), 2),
            "peak": round(max(c["value"] for c in cpu_usage), 2),
            "per_core_avg": [
                round(sum(core) / len(cpu_usage), 2)
                for core in zip(*(c["per_core"] for c in cpu_usage if "per_core" in c))
            ] if any("per_core" in c for c in cpu_usage) else [],
        },
        "memory": {
            "history": memory_usage[-100:],
            "average": round(sum(m["value"] for m in memory_usage) / len(memory_usage), 2),
            "peak": round(max(m["value"] for m in memory_usage), 2),
            "swap_avg": round(sum(m["swap"] for m in memory_usage) / len(memory_usage), 2),
        },
        "disk": {
            "history": disk_usage[-100:],
            "average": round(sum(d["value"] for d in disk_usage) / len(disk_usage), 2),
            "peak": round(max(d["value"] for d in disk_usage), 2),
            "io_stats": {
                "read": round(sum(d["read_bytes"] for d in disk_usage) / (1024 * 1024), 2),  # MB
                "write": round(sum(d["write_bytes"] for d in disk_usage) / (1024 * 1024), 2),  # MB
            },
        },
        "gpu": {
            "history": gpu_usage[-100:],
            "average": round(sum(g["usage"] for g in gpu_usage) / len(gpu_usage), 2) if gpu_usage else 0,
            "peak": round(max(g["usage"] for g in gpu_usage), 2) if gpu_usage else 0,
            "memory_avg": round(sum(g["memory"] for g in gpu_usage) / len(gpu_usage), 2) if gpu_usage else 0,
        },
        "network_interfaces": {
            iface: {
                "history": data[-100:],
                "total_download": round(sum(d["download"] for d in data) / (1024 * 1024), 2),  # MB
                "total_upload": round(sum(d["upload"] for d in data) / (1024 * 1024), 2),  # MB
                "errors": sum(d["errors"] for d in data),
                "drops": sum(d["drops"] for d in data),
            }
            for iface, data in network_interfaces.items()
        },
        "temperatures": {
            sensor: {
                "history": data[-100:],
                "average": round(sum(t["value"] for t in data) / len(data), 2),
                "peak": round(max(t["value"] for t in data), 2),
            }
            for sensor, data in temperatures.items()
        },
        "processes": process_stats,
    }

def calculate_session_duration(session: List[dict]) -> float:
    """Calculate session duration in hours."""
    if not session:
        return 0
    end_time = session[-1].last_updated if len(session) > 1 else datetime.now()
    return (end_time - session[0].last_updated).total_seconds() / 3600

def calculate_session_activities(session: List[dict]) -> List[dict]:
    """Calculate activities during a session."""
    activities = []
    current_activity = None
    activity_durations = defaultdict(int)
    process_durations = defaultdict(int)
    category_durations = defaultdict(int)
    hourly_activity = defaultdict(lambda: defaultdict(int))

    for i, state in enumerate(session):
        activity = state.attributes.get("activity")
        category = state.attributes.get("category", "Uncategorized")
        process = state.attributes.get("process", "Unknown")
        
        if activity != current_activity:
            duration = calculate_state_duration(state, session)
            hour = state.last_updated.hour
            
            activities.append({
                "activity": activity,
                "start": state.last_updated.isoformat(),
                "category": category,
                "process": process,
                "duration": duration,
                "details": {
                    "window_title": state.attributes.get("window_title", ""),
                    "url": state.attributes.get("url", ""),
                    "domain": state.attributes.get("domain", ""),
                },
            })
            
            activity_durations[activity] += duration
            process_durations[process] += duration
            category_durations[category] += duration
            hourly_activity[hour][category] += duration
            
            current_activity = activity

    # Create heatmap data
    heatmap_data = [
        {
            "hour": hour,
            "categories": [
                {"category": cat, "duration": round(duration)}
                for cat, duration in cats.items()
            ],
        }
        for hour, cats in sorted(hourly_activity.items())
    ]

    return {
        "timeline": activities,
        "summaries": {
            "activities": [
                {"name": activity, "duration": round(duration)}
                for activity, duration in activity_durations.items()
            ],
            "processes": [
                {"name": process, "duration": round(duration)}
                for process, duration in process_durations.items()
            ],
            "categories": [
                {"name": category, "duration": round(duration)}
                for category, duration in category_durations.items()
            ],
        },
        "heatmap": heatmap_data,
    }

def calculate_session_resources(session: List[dict]) -> dict:
    """Calculate resource usage during a session."""
    return {
        "cpu": [
            {
                "timestamp": state.last_updated.isoformat(),
                "value": state.attributes.get("cpu_percent", 0),
            }
            for state in session
        ],
        "memory": [
            {
                "timestamp": state.last_updated.isoformat(),
                "value": state.attributes.get("memory_percent", 0),
            }
            for state in session
        ],
    }

def calculate_session_network(session: List[dict]) -> dict:
    """Calculate network usage during a session."""
    total_download = sum(state.attributes.get("network_download", 0) for state in session)
    total_upload = sum(state.attributes.get("network_upload", 0) for state in session)

    return {
        "download": round(total_download / (1024 * 1024), 2),  # MB
        "upload": round(total_upload / (1024 * 1024), 2),
        "history": [
            {
                "timestamp": state.last_updated.isoformat(),
                "download": round(state.attributes.get("network_download", 0) / (1024 * 1024), 2),
                "upload": round(state.attributes.get("network_upload", 0) / (1024 * 1024), 2),
            }
            for state in session
        ],
    }

def calculate_peak_hours(history: List[dict]) -> List[dict]:
    """Calculate peak usage hours."""
    hourly_counts = defaultdict(int)
    for state in history:
        hour = state.last_updated.hour
        duration = calculate_state_duration(state, history)
        hourly_counts[hour] += duration

    # Find the top 5 peak hours
    peak_hours = sorted(
        [{"hour": hour, "usage": round(usage)} for hour, usage in hourly_counts.items()],
        key=lambda x: x["usage"],
        reverse=True,
    )[:5]

    return peak_hours

def calculate_hourly_usage(history: List[dict]) -> List[dict]:
    """Calculate usage by hour for the last 24 hours."""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    hourly_data = []
    for hour in range(24):
        time_point = yesterday + timedelta(hours=hour)
        usage = sum(
            calculate_state_duration(state, history)
            for state in history
            if time_point <= state.last_updated < time_point + timedelta(hours=1)
        )
        hourly_data.append({
            "hour": hour,
            "usage": round(usage),
            "timestamp": time_point.isoformat(),
        })

    return hourly_data

def calculate_category_comparison(history: List[dict]) -> dict:
    """Calculate category usage comparison."""
    category_usage = defaultdict(int)
    category_limits = {}
    
    for state in history:
        category = state.attributes.get("category", "Uncategorized")
        duration = calculate_state_duration(state, history)
        category_usage[category] += duration
        category_limits[category] = state.attributes.get("time_limit", 0)

    return {
        "usage": [
            {"category": cat, "usage": round(usage)}
            for cat, usage in category_usage.items()
        ],
        "limits": [
            {"category": cat, "limit": limit}
            for cat, limit in category_limits.items()
        ],
    }

def calculate_trend_analysis(history: List[dict], start_time: datetime) -> List[dict]:
    """Calculate usage trends over time."""
    daily_usage = defaultdict(lambda: defaultdict(int))
    
    for state in history:
        day = state.last_updated.date()
        category = state.attributes.get("category", "Uncategorized")
        duration = calculate_state_duration(state, history)
        daily_usage[day][category] += duration

    trend_data = []
    current = start_time.date()
    end = datetime.now().date()
    
    while current <= end:
        trend_data.append({
            "date": current.isoformat(),
            "categories": [
                {"name": cat, "usage": round(daily_usage[current][cat])}
                for cat in set(cat for day_usage in daily_usage.values() for cat in day_usage)
            ],
        })
        current += timedelta(days=1)

    return trend_data

def calculate_state_duration(state: dict, history: List[dict]) -> float:
    """Calculate duration of a state in minutes."""
    next_state = next(
        (s for s in history if s.last_updated > state.last_updated),
        None
    )
    duration = (
        (next_state.last_updated if next_state else datetime.now()) - state.last_updated
    ).total_seconds() / 60
    return duration

def calculate_period_stats(history: List[dict], start_time: datetime, end_time: datetime) -> List[dict]:
    """Calculate statistics for a specific time period."""
    categories: Dict[str, dict] = {}
    
    for state in history:
        if not (start_time <= state.last_updated <= end_time):
            continue

        category = state.attributes.get("category", "Uncategorized")
        if category not in categories:
            categories[category] = {
                "name": category,
                "timeUsed": 0,
                "timeLimit": state.attributes.get("time_limit", 0),
                "lastActivity": state.last_updated.isoformat(),
                "processes": {},
                "peakHours": defaultdict(int),
            }

        duration = calculate_state_duration(state, history)
        categories[category]["timeUsed"] += duration
        categories[category]["peakHours"][state.last_updated.hour] += duration
        
        process = state.attributes.get("process", "Unknown")
        if process not in categories[category]["processes"]:
            categories[category]["processes"][process] = 0
        categories[category]["processes"][process] += duration

    return [
        {
            "name": cat["name"],
            "timeUsed": round(cat["timeUsed"]),
            "timeLimit": cat["timeLimit"],
            "lastActivity": cat["lastActivity"],
            "topProcesses": sorted(
                [{"name": proc, "duration": round(duration)}
                 for proc, duration in cat["processes"].items()],
                key=lambda x: x["duration"],
                reverse=True,
            )[:5],
            "peakHours": sorted(
                [{"hour": hour, "usage": round(usage)}
                 for hour, usage in cat["peakHours"].items()],
                key=lambda x: x["usage"],
                reverse=True,
            )[:3],
        }
        for cat in categories.values()
    ] 