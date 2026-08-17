package com.bikemaster.ui.legal

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.bikemaster.R
import com.bikemaster.databinding.ActivityLegalBinding

class LegalActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLegalBinding

    companion object {
        fun start(context: Activity, titleRes: Int, contentRes: Int) {
            context.startActivity(Intent(context, LegalActivity::class.java).apply {
                putExtra("title_res", titleRes)
                putExtra("content_res", contentRes)
            })
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLegalBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val titleRes = intent.getIntExtra("title_res", R.string.privacy_policy)
        setTitle(getString(titleRes))
    }
}
