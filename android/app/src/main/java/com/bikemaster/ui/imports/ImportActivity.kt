package com.bikemaster.ui.imports

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bikemaster.R
import com.bikemaster.databinding.ActivityImportBinding
import com.bikemaster.network.ApiClient
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream

class ImportActivity : AppCompatActivity() {

    private lateinit var binding: ActivityImportBinding
    private var selectedFile: File? = null

    companion object {
        fun start(context: Activity) {
            context.startActivity(Intent(context, ImportActivity::class.java))
        }
    }

    private val pickGpxLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri ?: return@registerForActivityResult
        selectedFile = uriToFile(uri)
        uploadFile("gpx")
    }

    private val pickFitLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri ?: return@registerForActivityResult
        selectedFile = uriToFile(uri)
        uploadFile("fit")
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityImportBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnPickGpx.setOnClickListener { pickGpxLauncher.launch("application/gpx") }
        binding.btnPickFit.setOnClickListener { pickFitLauncher.launch("application/octet-stream") }
    }

    private fun uriToFile(uri: Uri): File {
        val inputStream = contentResolver.openInputStream(uri)!!
        val tempFile = File(cacheDir, "import_${System.currentTimeMillis()}")
        FileOutputStream(tempFile).use { output ->
            inputStream.copyTo(output)
        }
        inputStream.close()
        return tempFile
    }

    private fun uploadFile(type: String) {
        val file = selectedFile ?: return
        binding.progress.visibility = ProgressBar.VISIBLE
        binding.txtError.visibility = TextView.GONE
        binding.txtStatus.visibility = TextView.GONE

        lifecycleScope.launch {
            try {
                val requestFile = file.asRequestBody(type.toMediaTypeOrNull())
                val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
                val api = ApiClient.getApi(this@ImportActivity)
                val response = if (type == "gpx") api.importGpx(body) else api.importFit(body)
                binding.progress.visibility = ProgressBar.GONE
                binding.txtStatus.visibility = TextView.VISIBLE
                binding.txtStatus.text = "Import completato: uscita ${response.id}"
                Toast.makeText(this@ImportActivity, "Import completato", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                binding.progress.visibility = ProgressBar.GONE
                binding.txtError.visibility = TextView.VISIBLE
                binding.txtError.text = "Errore import: ${e.message}"
                Toast.makeText(this@ImportActivity, "Errore import", Toast.LENGTH_SHORT).show()
            } finally {
                file.delete()
            }
        }
    }
}
