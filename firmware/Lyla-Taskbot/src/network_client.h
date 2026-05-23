// firmware/src/network_client.h
// HTTP client for backend integration (Contract §6, §8, §9).
// Handles WiFi state, multipart POST, TTS fetch, and heartbeat.

#pragma once

#include <Arduino.h>

#include "sd_config.h"

namespace lyla {

struct AudioRequestTelemetry {
  String client_request_id;
  int wifi_rssi_dbm;
  int battery_pct;
  uint32_t recording_duration_ms;
};

struct AudioPostResult {
  int http_status;
  bool protocol_version_ok;
  String body;
  String error;
};

struct TtsFetchResult {
  int http_status;
  bool protocol_version_ok;
  uint8_t* bytes;
  size_t bytes_len;
  String error;
};

struct PendingCommand {
  String command_id;
  String command_type;
  String payload_json;
};

constexpr size_t LYLA_MAX_COMMANDS_PER_HEARTBEAT = 4;

struct HeartbeatResult {
  bool ok;
  int http_status;
  PendingCommand commands[LYLA_MAX_COMMANDS_PER_HEARTBEAT];
  size_t command_count;
};

bool network_init(const DeviceConfig& cfg);

bool network_wifi_connect(uint32_t timeout_ms);

bool network_wifi_is_connected();

int network_wifi_rssi();

void network_wifi_loop();

AudioPostResult network_post_audio(const DeviceConfig& cfg,
                                   const uint8_t* wav_pcm,
                                   size_t pcm_bytes,
                                   uint32_t sample_rate,
                                   const AudioRequestTelemetry& telemetry);

TtsFetchResult network_get_tts(const DeviceConfig& cfg, const String& fetch_url);

bool network_post_heartbeat(const DeviceConfig& cfg, bool online);

HeartbeatResult network_post_heartbeat_with_commands(const DeviceConfig& cfg,
                                                    bool online);

bool network_ack_command(const DeviceConfig& cfg, const String& command_id);

String network_generate_uuid_v4();

}
