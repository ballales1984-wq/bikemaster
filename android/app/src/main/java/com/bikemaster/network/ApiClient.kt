package com.bikemaster.network

import android.content.Context
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import com.bikemaster.utils.PreferencesManager

object ApiClient {
    
    fun getApi(context: Context): BikeMasterApi {
        val baseUrl = PreferencesManager.getBaseUrl(context)
        
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        
        val authInterceptor = Interceptor { chain ->
            val original = chain.request()
            val token = getToken(context)
            val requestBuilder = original.newBuilder()
                .addHeader("Accept", "application/json")
            if (!token.isNullOrEmpty()) {
                requestBuilder.addHeader("Authorization", "Bearer $token")
            }
            chain.proceed(requestBuilder.build())
        }
        
        val client = OkHttpClient.Builder()
            .addInterceptor(loggingInterceptor)
            .addInterceptor(authInterceptor)
            .build()
        
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(BikeMasterApi::class.java)
    }
    
    fun getToken(context: Context): String? {
        return context.getSharedPreferences("auth", Context.MODE_PRIVATE)
            .getString("token", null)
    }
}