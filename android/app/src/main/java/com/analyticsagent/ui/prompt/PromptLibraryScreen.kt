package com.analyticsagent.ui.prompt

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
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoGraph
import androidx.compose.material.icons.filled.Business
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.LocalOffer
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.analyticsagent.domain.model.AnalysisMode

/**
 * Enterprise Prompt Library with production-ready analytics templates for real companies.
 */
data class EnterprisePromptTemplate(
    val id: String,
    val category: String,
    val title: String,
    val targetAudience: String,
    val recommendedMode: AnalysisMode,
    val promptText: String,
    val keyMetrics: List<String>,
)

val ENTERPRISE_PROMPT_LIBRARY = listOf(
    EnterprisePromptTemplate(
        id = "csuite-exec",
        category = "Executive & C-Suite",
        title = "Executive Performance & Revenue Growth",
        targetAudience = "CEO / CFO / Board of Directors",
        recommendedMode = AnalysisMode.POWER_BI,
        promptText = "Architect an executive KPI dashboard evaluating Year-over-Year (YoY) revenue growth, quarterly EBITDA margin variance, and regional profit margins. Generate Star Schema relationships between Fact_Transactions and Dim_Date, Dim_Region, Dim_Product. Deliver DAX measures for YTD Revenue, Prior Year Revenue, YoY Variance %, and a Top 20% Pareto revenue driver measure.",
        keyMetrics = listOf("YoY Growth %", "YTD Revenue", "EBITDA Margin", "Pareto 80/20"),
    ),
    EnterprisePromptTemplate(
        id = "retail-ecommerce",
        category = "Retail & E-Commerce",
        title = "Customer Lifetime Value & Churn Risk",
        targetAudience = "Head of E-Commerce / Growth Lead",
        recommendedMode = AnalysisMode.POWER_BI,
        promptText = "Analyze transactional purchasing behavior to calculate Customer Lifetime Value (CLV), Average Order Value (AOV), and repeat customer purchase frequency. Identify customers at risk of churn (inactivity > 90 days). Generate DAX measures for 30-day Rolling AOV, Cohort Retention Rate, and Customer Segmentation into High-Value, Medium-Value, and Lapsed tiers.",
        keyMetrics = listOf("CLV", "AOV", "90-Day Churn Risk", "Cohort Retention"),
    ),
    EnterprisePromptTemplate(
        id = "finance-pl",
        category = "Finance & P&L",
        title = "Financial P&L & Expense Variance Analysis",
        targetAudience = "Finance Director / Controller",
        recommendedMode = AnalysisMode.EXCEL,
        promptText = "Perform full Income Statement & P&L variance analysis comparing Actual vs Budgeted figures across OpEx, CapEx, Cost of Goods Sold (COGS), and Gross Margin. Provide dynamic array formulas using LET, LAMBDA, and XLOOKUP for automated monthly rollups, and Power Query M-code for multi-entity ledger consolidation.",
        keyMetrics = listOf("Budget vs Actual Variance", "Gross Margin %", "OpEx Ratio", "Dynamic LET/XLOOKUP"),
    ),
    EnterprisePromptTemplate(
        id = "supply-chain",
        category = "Supply Chain & Ops",
        title = "Inventory Turnover & Stockout Risk",
        targetAudience = "VP of Supply Chain / Operations Lead",
        recommendedMode = AnalysisMode.POWER_BI,
        promptText = "Evaluate warehouse inventory health by calculating Days Sales of Inventory (DSI), Inventory Turnover Ratio, and reorder point thresholds. Flag stock-keeping units (SKUs) at imminent risk of stockout within 14 days and identify dead stock with zero movement in 180 days. Produce DAX measures for Safety Stock Buffer, Stockout Warning Count, and Carrying Cost.",
        keyMetrics = listOf("Days Sales Inventory (DSI)", "Stock Turnover", "Stockout Risk", "Dead Stock %"),
    ),
    EnterprisePromptTemplate(
        id = "hr-workforce",
        category = "HR & Workforce",
        title = "Workforce Headcount & Attrition Dynamics",
        targetAudience = "Chief People Officer / HR Analytics",
        recommendedMode = AnalysisMode.POWER_BI,
        promptText = "Analyze corporate workforce demographics, departmental attrition velocity, tenure distributions, and salary band parity. Calculate annualized voluntary vs involuntary turnover rate, hiring velocity, and average time-to-fill. Generate DAX measures for Active Headcount at Month End, Rolling 12-Month Attrition %, and Diversity Ratio across executive leadership tiers.",
        keyMetrics = listOf("Annualized Attrition %", "Active Headcount", "Tenure Distribution", "Comp-Ratio Parity"),
    ),
    EnterprisePromptTemplate(
        id = "marketing-funnel",
        category = "Marketing & Sales",
        title = "Marketing Attribution & Funnel Conversion",
        targetAudience = "Chief Marketing Officer / Sales VP",
        recommendedMode = AnalysisMode.POWER_BI,
        promptText = "Audit end-to-end B2B sales pipeline efficiency from Top of Funnel (MQLs) to Opportunity (SQLs) and Won Deals. Calculate Customer Acquisition Cost (CAC), CAC Payback Period in months, Lead-to-Close Velocity, and win rate by lead source channel. Generate DAX measures for Funnel Conversion Drop-off %, Pipeline Velocity ($/day), and Channel ROI multiplier.",
        keyMetrics = listOf("Customer Acquisition Cost", "Lead-to-Win Rate", "Pipeline Velocity", "Channel ROI"),
    ),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PromptLibraryScreen(
    onPromptSelected: (prompt: String, mode: AnalysisMode) -> Unit,
    onBack: () -> Unit,
) {
    var selectedCategory by remember { mutableStateOf("All Categories") }
    val categories = listOf("All Categories") + ENTERPRISE_PROMPT_LIBRARY.map { it.category }.distinct()

    val filteredTemplates = remember(selectedCategory) {
        if (selectedCategory == "All Categories") {
            ENTERPRISE_PROMPT_LIBRARY
        } else {
            ENTERPRISE_PROMPT_LIBRARY.filter { it.category == selectedCategory }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Enterprise Prompt Library", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text("Real-World Corporate Analytics Templates", style = MaterialTheme.typography.labelSmall, color = Color(0xFF00F2FE))
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
        Column(
            Modifier
                .fillMaxSize()
                .background(Color(0xFF0A0E17))
                .padding(padding)
        ) {
            // Category Filter Chips
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                categories.forEach { category ->
                    val isSelected = category == selectedCategory
                    FilterChip(
                        selected = isSelected,
                        onClick = { selectedCategory = category },
                        label = { Text(category, fontSize = 12.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Color(0xFF00F2FE),
                            selectedLabelColor = Color(0xFF0A0E17),
                            containerColor = Color(0xFF131A29),
                            labelColor = Color(0xFF94A3B8)
                        ),
                        border = FilterChipDefaults.filterChipBorder(
                            enabled = true,
                            selected = isSelected,
                            borderColor = if (isSelected) Color(0xFF00F2FE) else Color(0xFF1E293B)
                        )
                    )
                }
            }

            // Templates List
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                items(filteredTemplates, key = { it.id }) { template ->
                    EnterpriseTemplateCard(
                        template = template,
                        onSelect = { onPromptSelected(template.promptText, template.recommendedMode) }
                    )
                }
            }
        }
    }
}

@Composable
private fun EnterpriseTemplateCard(
    template: EnterprisePromptTemplate,
    onSelect: () -> Unit,
) {
    val modeColor = when (template.recommendedMode) {
        AnalysisMode.POWER_BI -> Color(0xFFF2C811)
        AnalysisMode.EXCEL -> Color(0xFF107C41)
        AnalysisMode.MYSQL -> Color(0xFF00758F)
        AnalysisMode.PYTHON -> Color(0xFF3B82F6)
        AnalysisMode.ALL -> Color(0xFFA855F7)
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(12.dp)),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            // Header Row: Category Badge + Mode Badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    template.category.uppercase(),
                    style = MaterialTheme.typography.labelSmall,
                    color = Color(0xFF00F2FE),
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.5.sp
                )
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(modeColor.copy(alpha = 0.15f))
                        .border(1.dp, modeColor.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        template.recommendedMode.name.replace("_", " "),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = modeColor
                    )
                }
            }

            Spacer(Modifier.height(8.dp))
            Text(template.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = Color.White)
            Spacer(Modifier.height(2.dp))
            Text("Audience: ${template.targetAudience}", style = MaterialTheme.typography.labelSmall, color = Color(0xFF94A3B8))

            Spacer(Modifier.height(10.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0xFF0A0E17))
                    .padding(10.dp)
            ) {
                Text(
                    template.promptText,
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFFCBD5E1),
                    lineHeight = 18.sp
                )
            }

            Spacer(Modifier.height(10.dp))
            // Key Metrics Tags
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                template.keyMetrics.forEach { metric ->
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(Color(0xFF1E293B))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(metric, fontSize = 10.sp, color = Color(0xFF94A3B8))
                    }
                }
            }

            Spacer(Modifier.height(14.dp))
            Button(
                onClick = onSelect,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(44.dp),
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF00F2FE),
                    contentColor = Color(0xFF0A0E17)
                )
            ) {
                Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.height(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Use This Corporate Prompt", fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        }
    }
}
