package com.analyticsagent.ui.prompt

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoGraph
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.DataObject
import androidx.compose.material.icons.filled.Dataset
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.SuggestionChipDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.analyticsagent.AppContainer
import com.analyticsagent.domain.model.AnalysisMode
import com.analyticsagent.navigation.Routes
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.LoadingBox
import com.analyticsagent.ui.components.SectionHeader
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.Formatters

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportPromptScreen(container: AppContainer, nav: NavController, projectId: String) {
    val vm: ReportPromptViewModel = viewModel(factory = VmFactory.from {
        ReportPromptViewModel(container.analysisRepository, container.datasetRepository)
    })
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(projectId) { vm.load(projectId) }

    // Listen for template selection from Enterprise Prompt Library
    val navBackStackEntry = nav.currentBackStackEntry
    LaunchedEffect(navBackStackEntry) {
        val selectedPrompt = navBackStackEntry?.savedStateHandle?.get<String>("selected_prompt")
        val selectedModeStr = navBackStackEntry?.savedStateHandle?.get<String>("selected_mode")
        if (!selectedPrompt.isNullOrBlank()) {
            val mode = selectedModeStr?.let {
                try { AnalysisMode.valueOf(it) } catch (_: Exception) { null }
            } ?: AnalysisMode.POWER_BI
            vm.setPromptAndMode(selectedPrompt, mode)
            navBackStackEntry.savedStateHandle.remove<String>("selected_prompt")
            navBackStackEntry.savedStateHandle.remove<String>("selected_mode")
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("AI Data Analyst", fontWeight = FontWeight.Bold)
                        Text("Analysis Spec & Mode", style = MaterialTheme.typography.labelSmall, color = Color(0xFF00F2FE))
                    }
                },
                navigationIcon = { TextButton(onClick = { nav.popBackStack() }) { Text("Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            if (state.loading) {
                item { LoadingBox("Loading project workspace…") }
            } else {
                // 1. Mode Switcher (Option 1: Excel | Option 2: PowerBI | Option 3: SQL)
                item {
                    Text(
                        "1. Select Analysis Mode",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Spacer(Modifier.height(8.dp))
                    ModeSelectorTabs(
                        selectedMode = state.selectedMode,
                        onModeSelected = { vm.setMode(it) }
                    )
                }

                // 2. Mode Capability Description Banner
                item {
                    ModeBanner(mode = state.selectedMode)
                }

                // Enterprise Prompt Library Access Card
                item {
                    Card(
                        onClick = { nav.navigate(Routes.PROMPT_LIBRARY) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, Color(0xFF00F2FE).copy(alpha = 0.5f), RoundedCornerShape(10.dp)),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Lightbulb, contentDescription = null, tint = Color(0xFF00F2FE), modifier = Modifier.size(20.dp))
                            Spacer(Modifier.width(10.dp))
                            Column(Modifier.weight(1f)) {
                                Text("Browse Enterprise Prompt Library", fontWeight = FontWeight.Bold, fontSize = 13.sp, color = Color(0xFF00F2FE))
                                Text("Pre-built real corporate templates (C-Suite, Retail, P&L, HR, Ops)", style = MaterialTheme.typography.bodySmall, color = Color(0xFF94A3B8), fontSize = 11.sp)
                            }
                            Text("Open", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = Color(0xFF00F2FE))
                        }
                    }
                }

                // 3. Prompt Input Box
                item {
                    SectionHeader(
                        "2. Business Prompt & Questions",
                        "Tell the AI what dimensions, metrics, time comparisons, and models you need.",
                    )
                    Spacer(Modifier.height(6.dp))
                    OutlinedTextField(
                        value = state.prompt,
                        onValueChange = vm::onPromptChange,
                        placeholder = {
                            Text(
                                when (state.selectedMode) {
                                    AnalysisMode.EXCEL -> "E.g., Generate dynamic array formulas (LET, LAMBDA, XLOOKUP), Power Query M-code, and automated Pivot Table macro."
                                    AnalysisMode.POWER_BI -> "E.g., Architect a Star Schema model, generate YoY/YTD DAX time-intelligence measures, and design an executive KPI dashboard."
                                    AnalysisMode.MYSQL -> "E.g., Write MySQL 8.0+ DDL schemas, Window function queries for MoM growth & running totals, and index recommendations."
                                    AnalysisMode.PYTHON -> "E.g., Write Pandas deduplication & cleaning pipeline, NumPy metric calculations, and Matplotlib/Seaborn visualization script."
                                    AnalysisMode.ALL -> "E.g., Full multi-stack report: Generate Excel formulas, Power BI DAX & Star Schema, MySQL queries, and Python analysis scripts."
                                }
                            )
                        },
                        minLines = 6,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Color(0xFF00F2FE),
                            unfocusedBorderColor = MaterialTheme.colorScheme.outline
                        )
                    )
                }

                // 4. Quick Suggestion Chips based on Mode
                item {
                    Text("Quick Prompt Ideas", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(6.dp))
                    PromptSuggestionChips(mode = state.selectedMode, onSelect = { vm.applyPromptTemplate(it) })
                }

                if (state.datasets.isEmpty()) {
                    item {
                        ErrorBox("No dataset found. Please upload a CSV/Excel file in the project first.")
                    }
                }
                if (state.error != null) {
                    item { ErrorBox(state.error!!) }
                }

                // 5. Submit Button
                item {
                    Button(
                        onClick = {
                            vm.generate { run ->
                                nav.navigate(Routes.runProgress(projectId, run.id))
                            }
                        },
                        enabled = !state.submitting && state.prompt.isNotBlank() && state.datasets.isNotEmpty(),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF00F2FE),
                            contentColor = Color(0xFF0A0E17)
                        )
                    ) {
                        if (state.submitting) {
                            CircularProgressIndicator(
                                Modifier.height(22.dp).width(22.dp),
                                strokeWidth = 2.dp,
                                color = Color(0xFF0A0E17)
                            )
                        } else {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.AutoGraph, contentDescription = null)
                                Spacer(Modifier.width(8.dp))
                                Text(
                                    "Generate ${when (state.selectedMode) {
                                        AnalysisMode.EXCEL -> "Excel Report & Formulas"
                                        AnalysisMode.POWER_BI -> "Power BI DAX & Data Model"
                                        AnalysisMode.MYSQL -> "MySQL Queries & Schemas"
                                        AnalysisMode.PYTHON -> "Python Analysis & Plot Scripts"
                                        AnalysisMode.ALL -> "Complete Multi-Stack Deliverables (All 4)"
                                    }}",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp
                                )
                            }
                        }
                    }
                }

                // 6. Prompt History
                if (state.promptHistory.isNotEmpty()) {
                    item {
                        Text(
                            "Recent Prompts",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    items(state.promptHistory, key = { it.runId }) { item ->
                        Card(
                            onClick = { vm.usePrompt(item.prompt) },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(10.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        ) {
                            Column(Modifier.padding(12.dp)) {
                                Text(
                                    "\"${item.prompt.take(90)}${if (item.prompt.length > 90) "…" else ""}\"",
                                    style = MaterialTheme.typography.bodyMedium
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "Status: ${item.status} · ${Formatters.formatDate(item.createdAt)}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ModeSelectorTabs(
    selectedMode: AnalysisMode,
    onModeSelected: (AnalysisMode) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF131A29))
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        ModeTabItem(
            title = "1. Excel Sirf",
            icon = Icons.Default.TableChart,
            isSelected = selectedMode == AnalysisMode.EXCEL,
            activeColor = Color(0xFF107C41),
            onClick = { onModeSelected(AnalysisMode.EXCEL) }
        )
        ModeTabItem(
            title = "2. PowerBI",
            icon = Icons.Default.AutoGraph,
            isSelected = selectedMode == AnalysisMode.POWER_BI,
            activeColor = Color(0xFFF2C811),
            textColor = if (selectedMode == AnalysisMode.POWER_BI) Color(0xFF0A0E17) else Color.White,
            onClick = { onModeSelected(AnalysisMode.POWER_BI) }
        )
        ModeTabItem(
            title = "3. MySQL",
            icon = Icons.Default.Code,
            isSelected = selectedMode == AnalysisMode.MYSQL,
            activeColor = Color(0xFF00758F),
            onClick = { onModeSelected(AnalysisMode.MYSQL) }
        )
        ModeTabItem(
            title = "4. Python",
            icon = Icons.Default.DataObject,
            isSelected = selectedMode == AnalysisMode.PYTHON,
            activeColor = Color(0xFF3B82F6),
            onClick = { onModeSelected(AnalysisMode.PYTHON) }
        )
        ModeTabItem(
            title = "5. All (Sabko)",
            icon = Icons.Default.AutoGraph,
            isSelected = selectedMode == AnalysisMode.ALL,
            activeColor = Color(0xFFA855F7),
            onClick = { onModeSelected(AnalysisMode.ALL) }
        )
    }
}

@Composable
private fun ModeTabItem(
    title: String,
    icon: ImageVector,
    isSelected: Boolean,
    activeColor: Color,
    textColor: Color = Color.White,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val bgAnim by animateColorAsState(
        targetValue = if (isSelected) activeColor else Color.Transparent,
        animationSpec = tween(durationMillis = 250, easing = FastOutSlowInEasing),
        label = "tabBg"
    )

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(bgAnim)
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                icon,
                contentDescription = null,
                tint = if (isSelected) textColor else Color(0xFF94A3B8),
                modifier = Modifier.padding(end = 6.dp).height(16.dp).width(16.dp)
            )
            Text(
                title,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                fontSize = 13.sp,
                color = if (isSelected) textColor else Color(0xFF94A3B8)
            )
        }
    }
}

@Composable
private fun ModeBanner(mode: AnalysisMode) {
    val (title, description, borderCol) = when (mode) {
        AnalysisMode.EXCEL -> Triple(
            "Excel Specialist (Sirf Excel)",
            "Generates dynamic array formulas (LET, LAMBDA, XLOOKUP), Power Query (M-Code) ETL scripts, and automated Pivot Tables.",
            Color(0xFF107C41)
        )
        AnalysisMode.POWER_BI -> Triple(
            "Power BI & DAX Architect",
            "Designs Star Schema data models (Fact/Dim tables, 1:N cardinality), Time-Intelligence DAX measures, and high-res Dashboard visuals.",
            Color(0xFFF2C811)
        )
        AnalysisMode.MYSQL -> Triple(
            "MySQL Database Specialist",
            "Generates MySQL 8.0+ DDL schemas with InnoDB indexes, Window functions (LAG, LEAD, running totals), and Common Table Expressions (CTEs).",
            Color(0xFF00758F)
        )
        AnalysisMode.PYTHON -> Triple(
            "Python Data Engineering & ML",
            "Generates reproducible Pandas data cleaning & deduplication scripts, NumPy metric calculations, and Matplotlib/Seaborn visualization scripts.",
            Color(0xFF3B82F6)
        )
        AnalysisMode.ALL -> Triple(
            "Multi-Stack Comprehensive (All 4 Engines)",
            "Generates EVERYTHING: Power BI DAX & Star Schema + Excel Dynamic Formulas + MySQL Queries + Python Analysis Scripts.",
            Color(0xFFA855F7)
        )
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, borderCol.copy(alpha = 0.4f), RoundedCornerShape(10.dp)),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Lightbulb, contentDescription = null, tint = borderCol, modifier = Modifier.height(16.dp))
                Spacer(Modifier.width(6.dp))
                Text(title, fontWeight = FontWeight.Bold, fontSize = 13.sp, color = borderCol)
            }
            Spacer(Modifier.height(4.dp))
            Text(description, style = MaterialTheme.typography.bodySmall, color = Color(0xFF94A3B8))
        }
    }
}

@Composable
private fun PromptSuggestionChips(
    mode: AnalysisMode,
    onSelect: (String) -> Unit
) {
    val chips = when (mode) {
        AnalysisMode.EXCEL -> listOf(
            "Dynamic Array Formulas & XLOOKUP",
            "Power Query ETL M-Code Script",
            "Automated VBA Pivot Dashboard Macro",
            "Month-over-Month Growth & YoY Formula"
        )
        AnalysisMode.POWER_BI -> listOf(
            "Star Schema & Relationship Model",
            "YoY & YTD Time-Intelligence Measures",
            "Pareto 80/20 & Top Product DAX",
            "Executive KPI Matrix & Dashboard Spec"
        )
        AnalysisMode.MYSQL -> listOf(
            "MySQL 8.0+ DDL Schema with InnoDB Indexes",
            "Window Functions (MoM Growth & Running Total)",
            "Pareto 80/20 CTE Ranking Query",
            "Cohort Retention & Churn Analysis Query"
        )
        AnalysisMode.PYTHON -> listOf(
            "Pandas Cleaning & Deduplication Script",
            "NumPy Financial KPI Aggregations",
            "Matplotlib & Seaborn Dark Theme Visuals",
            "IQR Outlier Detection & Moving Average"
        )
        AnalysisMode.ALL -> listOf(
            "All-in-One: DAX + Excel + MySQL + Python",
            "Full Corporate Data Stack Implementation",
            "End-to-End Enterprise Analytics Pipeline"
        )
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        chips.forEach { text ->
            SuggestionChip(
                onClick = { onSelect(text) },
                label = { Text(text, fontSize = 12.sp) },
                shape = RoundedCornerShape(8.dp),
                colors = SuggestionChipDefaults.suggestionChipColors(
                    containerColor = Color(0xFF131A29),
                    labelColor = Color(0xFF00F2FE)
                ),
                border = SuggestionChipDefaults.suggestionChipBorder(
                    enabled = true,
                    borderColor = Color(0xFF1E293B)
                )
            )
        }
    }
}
