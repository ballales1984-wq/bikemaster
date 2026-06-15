export interface Ride {
  id: number
  athlete_id: number
  name: string
  date: string
  duration_seconds: number
  distance_meters: number
  calories?: number
  avg_speed_kmh?: number
  max_speed_kmh?: number
  elev_gain_meters?: number
  elev_loss_meters?: number
  created_at?: string
}

export interface Athlete {
  id: number
  username: string
  email?: string
  is_admin?: boolean
  goal_type?: string
  goal_target?: number
  goal_current?: number
}

export interface Summary {
  rides: number
  distance_km: number
  calories: number
  avg_speed_kmh: number
  duration_minutes: number
}

export interface TrainingScore {
  label: string
  value: number
}

export interface CoachData {
  training_scores: TrainingScore[]
  training_advice: string
  historical_analysis?: string
  recovery_advice: string
}

export interface CalendarEvent {
  id: number
  athlete_id: number
  date: string
  title: string
  event_type: 'training' | 'race' | 'recovery' | 'goal_deadline' | 'test' | 'other'
  description?: string
  completed?: boolean
}

export interface Badge {
  id: number
  athlete_id: number
  badge_type: string
  title: string
  description: string
  earned_at: string
}