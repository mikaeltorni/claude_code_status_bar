//! Compact token and reset-time formatting for the status line.

use chrono::{Local, TimeZone};

/// Format a token count the way Python `int()` then the k/M thresholds do.
///
/// Fractional numbers truncate toward zero. Non-numeric text returns an empty
/// string. `None` and booleans are invalid.
pub fn format_tokens(value: &serde_json::Value) -> String {
    let Some(count) = token_count(value) else {
        return String::new();
    };
    if count >= 1_000_000 {
        return format!("{:.1}M", count as f64 / 1_000_000.0);
    }
    if count >= 1_000 {
        return format!("{:.1}k", count as f64 / 1_000.0);
    }
    count.to_string()
}

/// Truncate a finite number toward zero into a token count.
pub fn token_count(value: &serde_json::Value) -> Option<i64> {
    match value {
        serde_json::Value::Number(number) => {
            if let Some(integer) = number.as_i64() {
                return Some(integer);
            }
            number.as_f64().map(|value| value.trunc() as i64)
        }
        serde_json::Value::String(text) => text.parse::<i64>().ok(),
        _ => None,
    }
}

/// Format a Unix reset timestamp as time remaining from `now_secs`.
pub fn format_reset(value: &serde_json::Value, now_secs: i64) -> String {
    let Some(stamp) = token_count(value) else {
        return String::new();
    };
    let remaining = stamp - now_secs;
    if remaining <= 0 {
        return "now".to_string();
    }
    let hours = remaining / 3600;
    let minutes = (remaining % 3600) / 60;
    if hours > 0 {
        format!("{hours}h{minutes:02}m")
    } else {
        format!("{minutes}m")
    }
}

/// Format a Unix reset timestamp as a local weekday and clock time.
pub fn format_reset_day(value: &serde_json::Value) -> String {
    let Some(stamp) = token_count(value) else {
        return String::new();
    };
    Local
        .timestamp_opt(stamp, 0)
        .single()
        .map(|moment| moment.format("%a %H:%M").to_string())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::{format_reset, format_reset_day, format_tokens};
    use serde_json::json;

    #[test]
    fn formats_plain_thousands_and_millions() {
        assert_eq!(format_tokens(&json!(999)), "999");
        assert_eq!(format_tokens(&json!(1000)), "1.0k");
        assert_eq!(format_tokens(&json!(63249)), "63.2k");
        assert_eq!(format_tokens(&json!(1_000_000)), "1.0M");
    }

    #[test]
    fn truncates_fractional_tokens_before_formatting() {
        assert_eq!(format_tokens(&json!(999.9)), "999");
    }

    #[test]
    fn rejects_invalid_token_count() {
        assert_eq!(format_tokens(&json!("not-a-number")), "");
    }

    #[test]
    fn formats_hours_minutes_and_expired_resets() {
        assert_eq!(format_reset(&json!(1000 + 2 * 3600 + 13 * 60), 1000), "2h13m");
        assert_eq!(format_reset(&json!(1000 + 59 * 60), 1000), "59m");
        assert_eq!(format_reset(&json!(1000), 1000), "now");
    }

    #[test]
    fn rejects_invalid_reset_timestamp() {
        assert_eq!(format_reset(&json!("invalid"), 1000), "");
        assert_eq!(format_reset_day(&json!(null)), "");
    }
}
