package com.analyticsagent.ui.prompt

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
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoGraph
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DataObject
import androidx.compose.material.icons.filled.Dataset
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SummaryPreviewScreen(
    fileName: String,
    totalRows: Int,
    uniqueRecords: Int,
    duplicateRows: Int,
    duplicatesPercentage: Double,
    qualityScore: Double,
    executiveSummary: String,
    keyFindings: List<String>,
    onProceed: () -> Unit,
    onBack: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("AI Summary & Health Preview", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text("Verify Dataset Profile Before Full Generation", style = MaterialTheme.typography.labelSmall, color = Color(0xFF00F2FE))
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF0A0E17)),
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFF0A0E17))
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. Dataset Name Banner
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(12.dp)),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Dataset, contentDescription = null, tint = Color(0xFF00F2FE), modifier = Modifier.height(22.dp))
                        Spacer(Modifier.width(10.dp))
                        Column {
                            Text("INGESTED DATASET", style = MaterialTheme.typography.labelSmall, color = Color(0xFF94A3B8))
                            Text(fileName, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = Color.White)
                        }
                    }
                }
            }

            // 2. Duplicates vs Unique Records KPI Grid
            item {
                Text("Deduplication & Data Integrity Overview", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
                Spacer(Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    KpiMetricBox(
                        title = "TOTAL ROWS",
                        value = "%,d".format(totalRows),
                        color = Color.White,
                        modifier = Modifier.weight(1f)
                    )
                    KpiMetricBox(
                        title = "UNIQUE RECORDS",
                        value = "%,d".format(uniqueRecords),
                        color = Color(0xFF10B981),
                        modifier = Modifier.weight(1f)
                    )
                }
                Spacer(Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    KpiMetricBox(
                        title = "DUPLICATES",
                        value = "${"%,d".format(duplicateRows)} (%.1f%%)".format(duplicatesPercentage),
                        color = if (duplicateRows > 0) Color(0xFFF59E0B) else Color(0xFF10B981),
                        modifier = Modifier.weight(1f)
                    )
                    KpiMetricBox(
                        title = "QUALITY SCORE",
                        value = "%.1f%%".format(qualityScore),
                        color = Color(0xFF00F2FE),
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            // 3. AI Executive Summary Card
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, Color(0xFF00F2FE).copy(alpha = 0.3f), RoundedCornerShape(12.dp)),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Insights, contentDescription = null, tint = Color(0xFF00F2FE), modifier = Modifier.height(18.dp))
                            Spacer(Modifier.width(8.dp))
                            Text("AI Executive Summary Preview", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = Color(0xFF00F2FE))
                        }
                        Spacer(Modifier.height(10.dp))
                        Text(
                            executiveSummary,
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color(0xFFE2E8F0),
                            lineHeight = 20.sp
                        )
                    }
                }
            }

            // 4. Data Health & Ingestion Findings
            if (keyFindings.isNotEmpty()) {
                item {
                    Text("Preliminary Integrity Findings", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
                }
                items(keyFindings) { finding ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.Top) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF10B981), modifier = Modifier.height(18.dp).padding(top = 2.dp))
                            Spacer(Modifier.width(8.dp))
                            Text(finding, style = MaterialTheme.typography.bodySmall, color = Color(0xFFCBD5E1), lineHeight = 18.sp)
                        }
                    }
                }
            }

            // 5. Action Buttons
            item {
                Spacer(Modifier.height(8.dp))
                Button(
                    onClick = onProceed,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF00F2FE),
                        contentColor = Color(0xFF0A0E17)
                    )
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.AutoGraph, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Generate Full Report, DAX & Dashboard PDF", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    }
                }

                Spacer(Modifier.height(8.dp))
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(44.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.height(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Adjust Prompt or Select Another Template", fontSize = 13.sp)
                }
            }
        }
    }
}

@Composable
private fun KpiMetricBox(
    title: String,
    value: String,
    color: Color,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.border(1.dp, Color(0xFF1E293B), RoundedCornerShape(10.dp)),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(title, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF94A3B8), letterSpacing = 0.5.sp)
            Spacer(Modifier.height(4.dp))
            Text(value, fontSize = 15.sp, fontWeight = FontWeight.Bold, color = color)
        }
    }
}
