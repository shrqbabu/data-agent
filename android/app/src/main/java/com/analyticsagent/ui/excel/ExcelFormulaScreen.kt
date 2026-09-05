package com.analyticsagent.ui.excel

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.DataObject
import androidx.compose.material.icons.filled.Functions
import androidx.compose.material.icons.filled.IntegrationInstructions
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.analyticsagent.domain.model.ExcelFormula

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExcelFormulaScreen(
    nav: NavController,
    formulas: List<ExcelFormula>
) {
    val context = LocalContext.current

    fun copy(text: String, label: String) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
        Toast.makeText(context, "Copied: $label", Toast.LENGTH_SHORT).show()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Excel Formulas & Macros", fontWeight = FontWeight.Bold)
                        Text("Dynamic Arrays, M-Code & VBA", style = MaterialTheme.typography.labelSmall, color = Color(0xFF107C41))
                    }
                },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        if (formulas.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("No Excel formulas generated for this run.", color = Color(0xFF94A3B8))
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                items(formulas, key = { it.name }) { item ->
                    ExcelFormulaCard(item = item, onCopy = { copy(it, item.name) })
                }
            }
        }
    }
}

@Composable
private fun ExcelFormulaCard(
    item: ExcelFormula,
    onCopy: (String) -> Unit
) {
    val categoryColor = when (item.category) {
        "Power Query" -> Color(0xFF8B5CF6)
        "VBA" -> Color(0xFFF59E0B)
        "Dynamic Array" -> Color(0xFF107C41)
        else -> Color(0xFF00F2FE)
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(12.dp)),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(Modifier.padding(14.dp)) {
            // Header: Name + Category badge + Copy Button
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(item.name, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color.White)
                    if (item.targetRange.isNotBlank()) {
                        Text("Target: ${item.targetRange}", fontSize = 11.sp, color = Color(0xFF94A3B8))
                    }
                }
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(categoryColor.copy(alpha = 0.15f))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(item.category.uppercase(), fontSize = 10.sp, fontWeight = FontWeight.Bold, color = categoryColor)
                }
            }

            Spacer(Modifier.height(10.dp))

            // Main Formula / Script Box
            val codeToDisplay = item.mCode ?: item.vbaCode ?: item.formula
            Box(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFF0A0E17))
                    .padding(10.dp)
            ) {
                Text(
                    codeToDisplay,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    color = Color(0xFF00F2FE)
                )
            }

            Spacer(Modifier.height(8.dp))

            // Explanation
            if (item.explanation.isNotBlank()) {
                Text(item.explanation, style = MaterialTheme.typography.bodySmall, color = Color(0xFF94A3B8))
            }

            if (item.exampleOutput.isNotBlank()) {
                Spacer(Modifier.height(4.dp))
                Text("Result: ${item.exampleOutput}", fontSize = 11.sp, color = Color(0xFF10B981), fontWeight = FontWeight.SemiBold)
            }

            Spacer(Modifier.height(10.dp))

            // Copy Button
            Button(
                onClick = { onCopy(codeToDisplay) },
                modifier = Modifier.fillMaxWidth().height(36.dp),
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF1E293B),
                    contentColor = Color(0xFF00F2FE)
                )
            ) {
                Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.height(14.dp))
                Spacer(Modifier.width(6.dp))
                Text("Copy to Clipboard", fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
