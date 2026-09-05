package com.analyticsagent.ui.schema

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
import androidx.compose.material.icons.filled.AccountTree
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.DataObject
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material.icons.filled.ViewModule
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
import com.analyticsagent.domain.model.StarRelationship
import com.analyticsagent.domain.model.StarSchemaModel
import com.analyticsagent.domain.model.StarTable

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StarSchemaScreen(
    nav: NavController,
    starSchema: StarSchemaModel?
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
                        Text("Star Schema Data Model", fontWeight = FontWeight.Bold)
                        Text("Power BI Relational Architecture", style = MaterialTheme.typography.labelSmall, color = Color(0xFFF2C811))
                    }
                },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                actions = {
                    if (starSchema?.dateTableDax != null) {
                        IconButton(onClick = { copy(starSchema.dateTableDax, "Date Table DAX") }) {
                            Icon(Icons.Default.ContentCopy, contentDescription = "Copy Date DAX", tint = Color(0xFF00F2FE))
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        if (starSchema == null) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("No Star Schema model available for this run.", color = Color(0xFF94A3B8))
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 1. Fact Tables Section
                item {
                    SectionTitle(
                        title = "1. Fact Tables (Metrics & Transactions)",
                        color = Color(0xFF00F2FE),
                        icon = Icons.Default.TableChart
                    )
                }
                items(starSchema.factTables) { table ->
                    TableNodeCard(table = table, isFact = true)
                }

                // 2. Relationships Mapping
                if (starSchema.relationships.isNotEmpty()) {
                    item {
                        Spacer(Modifier.height(8.dp))
                        SectionTitle(
                            title = "2. Relationship Cardinality (1:N)",
                            color = Color(0xFF8B5CF6),
                            icon = Icons.Default.AccountTree
                        )
                    }
                    items(starSchema.relationships) { rel ->
                        RelationshipCard(rel)
                    }
                }

                // 3. Dimension Tables Section
                if (starSchema.dimensionTables.isNotEmpty()) {
                    item {
                        Spacer(Modifier.height(8.dp))
                        SectionTitle(
                            title = "3. Dimension Tables (Conformed Filters)",
                            color = Color(0xFF10B981),
                            icon = Icons.Default.ViewModule
                        )
                    }
                    items(starSchema.dimensionTables) { table ->
                        TableNodeCard(table = table, isFact = false)
                    }
                }

                // 4. Recommended Date Table DAX Script
                if (!starSchema.dateTableDax.isNullOrBlank()) {
                    item {
                        Spacer(Modifier.height(8.dp))
                        SectionTitle(
                            title = "4. Power BI Date Table DAX Script",
                            color = Color(0xFFF59E0B),
                            icon = Icons.Default.CalendarToday
                        )
                        Spacer(Modifier.height(6.dp))
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(12.dp)),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("Dim_Date Table DAX", fontWeight = FontWeight.Bold, color = Color(0xFFF59E0B))
                                    OutlinedButton(onClick = { copy(starSchema.dateTableDax, "Date Table DAX") }) {
                                        Text("Copy DAX", fontSize = 12.sp)
                                    }
                                }
                                Spacer(Modifier.height(8.dp))
                                Box(
                                    Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(8.dp))
                                        .background(Color(0xFF0A0E17))
                                        .padding(10.dp)
                                ) {
                                    Text(
                                        starSchema.dateTableDax,
                                        fontFamily = FontFamily.Monospace,
                                        fontSize = 11.sp,
                                        color = Color(0xFFE2E8F0)
                                    )
                                }
                            }
                        }
                    }
                }

                // 5. Best Practice Notes
                if (starSchema.modelingRecommendations.isNotEmpty()) {
                    item {
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "Architectural Guidelines",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Spacer(Modifier.height(6.dp))
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            starSchema.modelingRecommendations.forEach { rec ->
                                Row(verticalAlignment = Alignment.Top) {
                                    Text("• ", color = Color(0xFF00F2FE), fontWeight = FontWeight.Bold)
                                    Text(rec, style = MaterialTheme.typography.bodySmall, color = Color(0xFF94A3B8))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionTitle(title: String, color: Color, icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = color, modifier = Modifier.height(18.dp))
        Spacer(Modifier.width(8.dp))
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = color)
    }
}

@Composable
private fun TableNodeCard(table: StarTable, isFact: Boolean) {
    val borderColor = if (isFact) Color(0xFF00F2FE) else Color(0xFF10B981)
    val badgeBg = if (isFact) Color(0xFF00F2FE).copy(alpha = 0.15f) else Color(0xFF10B981).copy(alpha = 0.15f)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, borderColor.copy(alpha = 0.5f), RoundedCornerShape(12.dp)),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(table.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(badgeBg)
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        if (isFact) "FACT TABLE" else "DIMENSION",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = borderColor
                    )
                }
            }

            if (table.primaryKey != null) {
                Spacer(Modifier.height(6.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Key, contentDescription = null, tint = Color(0xFFF59E0B), modifier = Modifier.height(14.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Primary Key: ${table.primaryKey}", fontSize = 11.sp, color = Color(0xFFF59E0B), fontWeight = FontWeight.SemiBold)
                }
            }

            Spacer(Modifier.height(8.dp))
            Text(table.description, style = MaterialTheme.typography.bodySmall, color = Color(0xFF94A3B8))

            Spacer(Modifier.height(10.dp))
            Text("Columns:", fontSize = 11.sp, color = Color(0xFF64748B), fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(4.dp))
            Text(
                table.columns.joinToString("  •  "),
                fontFamily = FontFamily.Monospace,
                fontSize = 11.sp,
                color = Color(0xFFE2E8F0)
            )
        }
    }
}

@Composable
private fun RelationshipCard(rel: StarRelationship) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(10.dp)),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0A0E17)),
        shape = RoundedCornerShape(10.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    "${rel.fromTable}[${rel.fromColumn}]",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF10B981)
                )
                Text("Dimension (1)", fontSize = 10.sp, color = Color(0xFF64748B))
            }

            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .background(Color(0xFF8B5CF6).copy(alpha = 0.2f))
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Text(
                    "➔ ${rel.cardinality} (${rel.crossFilterDirection}) ➔",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF8B5CF6)
                )
            }

            Column(Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                Text(
                    "${rel.toTable}[${rel.toColumn}]",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF00F2FE)
                )
                Text("Fact (Many)", fontSize = 10.sp, color = Color(0xFF64748B))
            }
        }
    }
}
