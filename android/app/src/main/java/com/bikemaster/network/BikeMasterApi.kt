package com.bikemaster.network

import com.bikemaster.models.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface BikeMasterApi {
    
    @GET("health")
    suspend fun healthCheck(): Map<String, String>
    
    @FormUrlEncoded
    @POST("auth/login")
    suspend fun login(
        @Field("username") username: String,
        @Field("password") password: String
    ): AuthResponse
    
    @POST("auth/register")
    suspend fun register(@Body map: Map<String, String>): Map<String, Any>
    
    @GET("rides")
    suspend fun getRides(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("sort") sort: String = "date"
    ): RideResponse
    
    @GET("rides/{rideId}")
    suspend fun getRide(@Path("rideId") rideId: Int): Ride
    
    @DELETE("rides/{rideId}")
    suspend fun deleteRide(@Path("rideId") rideId: Int)
    
    @GET("athletes")
    suspend fun getAthletes(): Map<String, List<AthleteProfile>>
    
    @GET("athletes/{athleteId}")
    suspend fun getAthlete(@Path("athleteId") athleteId: Int): AthleteProfile
    
    @PUT("athletes/{athleteId}")
    suspend fun updateAthlete(@Path("athleteId") athleteId: Int, @Body athlete: AthleteProfile)
    
    @GET("training/load")
    suspend fun getTrainingLoad(
        @Query("athlete_id") athleteId: Int,
        @Query("days") days: Int = 30
    ): TrainingLoad
    
    @GET("coach/workout")
    suspend fun getWorkoutRecommendations(@Query("athlete_id") athleteId: Int): WorkoutRecommendation
    
    @GET("coach/full")
    suspend fun getCoachFullData(@Query("athlete_id") athleteId: Int): Map<String, Any>
    
    @GET("dashboard")
    suspend fun getDashboard(): Map<String, Any>
    
    @GET("calendar/events")
    suspend fun getCalendarEvents(
        @Query("athlete_id") athleteId: Int,
        @Query("year") year: Int,
        @Query("month") month: Int
    ): Map<String, List<CalendarEvent>>
    
    @POST("calendar/events")
    suspend fun createCalendarEvent(@Body event: CalendarEvent)
    
    @Multipart
    @POST("import/gpx")
    suspend fun importGpx(
        @Part file: MultipartBody.Part
    ): Ride
    
    @Multipart
    @POST("import/fit")
    suspend fun importFit(
        @Part file: MultipartBody.Part
    ): Ride

    @POST("athletes/{athleteId}/health-metrics")
    suspend fun addHealthMetrics(
        @Path("athleteId") athleteId: Int,
        @Body metrics: List<Map<String, Any?>>
    ): Map<String, Any>

    @GET("weather")
    suspend fun getWeather(
        @Query("lat") lat: Double,
        @Query("lon") lon: Double,
        @Query("date") date: String? = null
    ): Map<String, Any>
}