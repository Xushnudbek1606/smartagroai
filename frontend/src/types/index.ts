export type Role = 'admin' | 'farmer' | 'agronom';
export type Language = 'uz-Latn' | 'uz-Cyrl' | 'en' | 'ru';

export interface User {
  id: string;
  full_name: string;
  username: string;
  role: Role;
  telegram_id: string | null;
  telegram_username: string | null;
  phone: string | null;
  region: string | null;
  district: string | null;
  preferred_language: Language;
  avatar_url: string | null;
  is_active: boolean;
  must_change_password: boolean;
  telegram_notifications_enabled: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface BoundaryGeoJSON {
  type: 'Polygon' | 'Point';
  coordinates: number[] | number[][] | number[][][];
}

export interface Farm {
  id: string;
  owner_id: string;
  name: string;
  region: string;
  district: string;
  area_hectares: number | null;
  notes: string | null;
  boundary: BoundaryGeoJSON | null;
  center_lat: number | null;
  center_lng: number | null;
  created_at: string;
  updated_at: string;
  crops_count: number;
}

export interface Crop {
  id: string;
  farm_id: string;
  name: string;
  variety: string | null;
  planting_date: string | null;
  area_hectares: number | null;
  status: 'planned' | 'growing' | 'harvested' | 'failed';
  notes: string | null;
  created_at: string;
  updated_at: string;
  farm_name: string | null;
}

export interface Diagnosis {
  id: string;
  farmer_id: string;
  crop_id: string | null;
  image_url: string;
  predicted_crop: string | null;
  disease_name: string | null;
  confidence: number | null;
  severity: 'low' | 'medium' | 'high' | 'unknown' | null;
  symptoms: string[] | null;
  recommendations: string[] | null;
  next_steps: string | null;
  region: string | null;
  user_notes: string | null;
  model_version: string | null;
  status: 'completed' | 'no_finding' | string;
  language: string;
  created_at: string;
}

export interface IntegrationStatus {
  configured: boolean;
  provider: string | null;
  model: string | null;
}

export interface Subscription {
  plan: 'free' | 'pro';
  role: Role;
  diagnoses_used: number;
  diagnoses_limit: number; // -1 = unlimited
  advice_used: number;
  advice_limit: number; // -1 = unlimited
  diagnoses_remaining: number | null;
  advice_remaining: number | null;
  unlimited: boolean;
  paid_until: string | null;
  features: string[];
}

export interface SubscriptionAdmin extends Subscription {
  user_id: string;
  username: string | null;
}

export interface WeatherCurrent {
  location: string;
  provider: string;
  fetched_at: string;
  expires_at: string;
  temperature: number;
  feels_like: number;
  humidity: number;
  wind_speed: number;
  description: string;
  icon: string | null;
  precipitation_probability: number | null;
  cloudiness: number | null;
  sun_rise: string | null;
  sun_set: string | null;
}

export interface WeatherDay {
  date: string;
  temp_min: number;
  temp_max: number;
  description: string;
  icon: string | null;
  precipitation_probability: number | null;
  humidity: number | null;
  wind_speed: number | null;
}

export interface WeatherForecast {
  location: string;
  provider: string;
  fetched_at: string;
  expires_at: string;
  days: WeatherDay[];
  advisories: string[];
}

export interface WeatherRegion {
  region: string;
  districts: string[];
}

export interface Conversation {
  id: string;
  farmer_id: string;
  agronomist_id: string;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  unread_count: number;
  partner: User | null;
  last_message_preview: string | null;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  message_text: string | null;
  attachment_url: string | null;
  attachment_name: string | null;
  read_at: string | null;
  created_at: string;
}

export interface AppNotification {
  id: string;
  title: string;
  body: string | null;
  type: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface AdminStatistics {
  total_users: number;
  total_farmers: number;
  total_agronomists: number;
  total_admins: number;
  active_users: number;
  total_farms: number;
  total_crops: number;
  total_diagnoses: number;
  diagnoses_today: number;
  diagnoses_week: number;
  total_conversations: number;
  messages_total: number;
  users_registered_today: number;
  activity: { date: string; diagnoses: number; registrations: number }[];
}

export interface AuditLog {
  id: string;
  actor_id: string | null;
  actor_name: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface SystemHealth {
  status: string;
  database: string;
  weather_api: IntegrationStatus;
  ai_service: IntegrationStatus;
  telegram_bot: { configured: boolean; online: boolean; last_heartbeat?: string };
  redis: string;
  version: string;
  environment: string;
  checked_at: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
