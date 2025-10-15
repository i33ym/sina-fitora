//enums
type Gender = 'male' | 'female';
type ActivenessLevel = 'sedentary' | 'lightly_active' | 'moderately_active' | 'very_active' | 'extremely_active';
type Goal = 'lose_weight' | 'maintain_weight' | 'gain_weight';
type MealTime = 'breakfast' | 'lunch' | 'dinner' | 'snack';
type RequestStatus = 'pending' | 'approved' | 'rejected';
type Motivation = 'vocation' | 'health' | 'appearance' | 'other';
type PreferredDiet = 'artificial_intelligence' | 'vegetarian' | 'vegan' | 'keto' | 'paleo' | 'mediterranean' | 'other';

//auth.types
interface LoginRequest {
    phone_number: string;
    password: string
}

interface LoginResponse {
    token: string
}

//client.types

interface Client {
    id: number,
    email: string, 
    phone_number: string;
    first_name: string;
    last_name: string;
    gender: Gender;
    date_of_birth: Date,
    current_height: number,
    current_weight: number,
    target_weight: number,
    target_date: Date,
    activeness_level: ActivenessLevel,
    goal: Goal,
    motivation: Motivation,
    preferred_diet: PreferredDiet,
    diet_restrictions: string[];
    profile_completed: boolean
}

interface ClientProfile {
    
    id: number,
    email: string, 
    phone_number: string;
    first_name: string;
    last_name: string;
    gender: string;
    date_of_birth: string,
    current_height: string,
    current_weight: string,
    target_weight: string,
    target_date: Date,
    activeness_level: string,
    goal: string,
    motivation: string,
    preferred_diet: string
    diet_restrictions: string[],
    profile_completed: boolean,
    meals: Meal
}

interface ClientDetail {
    profile: Client;
    meals: Meal[];
    total_meals: number;
}

interface Meal {
    id: number;
    image_url: string;
    meal_date: Date;
    foods_data: string;
    meal_time: MealTime
    created_at: Date,
    updated_at: Date
}

//group.types
interface Group {
    id: number,
    name: string,
    code: string,
    created_at: Date,
    updated_at: Date
}

interface CreateGroupRequest {
    name: string;
    code: string
}

interface CreateGroupResponse {
  id: number;
  name: string;
  code: string;
  created_at: Date,
  updated_at: Date
}

interface UpdateGroupRequest {
    name: string;
    code: string;
}

interface UpdateGroupResponse {
  id: number;
  name: string,
  code: string;
  created_at: Date
  updated_at: Date
}

//request.types
interface RequsetUser {
    id: number;
    first_name: string;
    last_name: string;
    gender: string;
    date_of_birth: string;
}

interface JoinRequest {
    id: number;
    user: RequsetUser;
    group_name: string;
    status: string;
    requested_at: string;
    responsed_at: string;
}
//api.response.type
interface ApiResponse<T> {
    success: boolean;
    data: T;
    message?: string;
}

interface ApiError {
    message: string;
    status?: number;
    errors?: Record<string, string[]>;
}
