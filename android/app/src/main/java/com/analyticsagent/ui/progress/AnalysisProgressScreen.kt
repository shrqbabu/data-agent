package com.analyticsagent.ui.progress

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoGraph
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.Code
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.draw.scale
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
import com.analyticsagent.navigation.Routes
import com.analyticsagent.ui.components.ErrorBox
import com.analyticsagent.ui.components.VmFactory
import com.analyticsagent.util.Formatters

data class PipelineStageStep(
    val id: String,
    val title: String,
    val activeDescription: String,
    val icon: ImageVector,
    val minProgress: Int,
)

val PIPELINE_STEPS = listOf(
    PipelineStageStep(
        id = "READ",
        title = "Reading Dataset",
        activeDescription = "Ingesting CSV/Excel, parsing headers and normalizing schema...",
        icon = Icons.Default.FolderOpen,
        minProgress = 0,
    ),
    PipelineStageStep(
        id = "PROFILE",
        title = "Profiling Duplicates & Uniques",
        activeDescription = "Calculating duplicate rows vs unique entities & null percentages...",
        icon = Icons.Default.Search,
        minProgress = 12,
    ),
    PipelineStageStep(
        id = "MODEL",
        title = "Data Cleaning & Star Schema Modeling",
        activeDescription = "Architecting Fact & Dimension tables with 1:N cardinality...",
        icon = Icons.Default.CleaningServices,
        minProgress = 25,
    ),
    PipelineStageStep(
        id = "CALCULATE",
        title = "Deterministic Calculations",
        activeDescription = "Computing metric registers, growth rates, margins & statistical rankings...",
        icon = Icons.Default.Psychology,
        minProgress = 42,
    ),
    PipelineStageStep(
        id = "SYNTHESIZE",
        title = "DAX & Formula Synthesis",
        activeDescription = "Writing production-ready DAX time-intelligence & Excel dynamic formulas...",
        icon = Icons.Default.Code,
        minProgress = 65,
    ),
    PipelineStageStep(
        id = "VISUALS",
        title = "Rendering Suggested Dashboard Visual",
        activeDescription = "Synthesizing high-resolution analytical visual charts & KPI cards...",
        icon = Icons.Default.Dashboard,
        minProgress = 80,
    ),
    PipelineStageStep(
        id = "PDF",
        title = "Compiling Executive PDF Report",
        activeDescription = "Generating multi-page PDF with final report & embedded dashboard...",
        icon = Icons.Default.Description,
        minProgress = 90,
    ),
    PipelineStageStep(
        id = "VERIFY",
        title = "Validation & Delivery",
        activeDescription = "Verifying analytical integrity and finalizing deliverables...",
        icon = Icons.Default.Verified,
        minProgress = 98,
    ),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalysisProgressScreen(
    container: AppContainer,
    nav: NavController,
    projectId: String,
    runId: String
) {
    val vm: AnalysisProgressViewModel = viewModel(factory = VmFactory.from {
        AnalysisProgressViewModel(container.analysisRepository)
    })
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(runId) { vm.startPolling(runId) }

    // Navigate to results when done
    LaunchedEffect(state.done) {
        if (state.done && state.run?.isSuccess == true) {
            nav.navigate(Routes.runResults(projectId, runId)) {
                popUpTo(Routes.project(projectId)) { inclusive = false }
            }
        }
    }

    val run = state.run
    val currentProgress = run?.progress ?: 5
    val currentStage = run?.stage ?: "VALIDATING_INPUT"

    // Infinite pulse for currently active stage
    val infiniteTransition = rememberInfiniteTransition(label = "stepPulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1.0f,
        targetValue = 1.18f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseScale"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("AI Analytics Pipeline", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text("Live Execution Engine", style = MaterialTheme.typography.labelSmall, color = Color(0xFF00F2FE))
                    }
                },
                navigationIcon = {
                    TextButton(onClick = { nav.popBackStack() }) {
                        Text("Back", color = Color(0xFF94A3B8))
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
            // Header Progress Card with Glowing Bar
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
                    .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(12.dp)),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF131A29)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                if (run?.isSuccess == true) "Analysis Complete!" else "AI Agent Processing...",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = if (run?.isSuccess == true) Color(0xFF10B981) else Color.White
                            )
                            Text(
                                Formatters.humanReadableStage(currentStage),
                                style = MaterialTheme.typography.bodySmall,
                                color = Color(0xFF00F2FE)
                            )
                        }
                        Text(
                            "$currentProgress%",
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF00F2FE)
                        )
                    }

                    Spacer(Modifier.height(12.dp))
                    val animatedProgress by animateFloatAsState(
                        targetValue = currentProgress / 100.0f,
                        animationSpec = tween(500),
                        label = "progressAnim"
                    )
                    LinearProgressIndicator(
                        progress = { animatedProgress },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = Color(0xFF00F2FE),
                        trackColor = Color(0xFF1E293B)
                    )
                }
            }

            if (state.error != null) {
                Box(Modifier.padding(horizontal = 16.dp)) {
                    ErrorBox(state.error!!)
                }
                Spacer(Modifier.height(12.dp))
            }

            // Animated Step-by-Step Pipeline Timeline
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                itemsIndexed(PIPELINE_STEPS) { index, step ->
                    val isCompleted = currentProgress > step.minProgress + 10 || run?.isSuccess == true
                    val isCurrent = !isCompleted && currentProgress >= step.minProgress && run?.isSuccess != true
                    val isPending = currentProgress < step.minProgress

                    AnimatedPipelineStepRow(
                        step = step,
                        index = index + 1,
                        isCompleted = isCompleted,
                        isCurrent = isCurrent,
                        isPending = isPending,
                        pulseScale = if (isCurrent) pulseScale else 1.0f
                    )
                }
            }
        }
    }
}

@Composable
private fun AnimatedPipelineStepRow(
    step: PipelineStageStep,
    index: Int,
    isCompleted: Boolean,
    isCurrent: Boolean,
    isPending: Boolean,
    pulseScale: Float,
) {
    val borderColor by animateColorAsState(
        targetValue = when {
            isCompleted -> Color(0xFF10B981).copy(alpha = 0.5f)
            isCurrent -> Color(0xFF00F2FE).copy(alpha = 0.8f)
            else -> Color(0xFF1E293B)
        },
        label = "borderAnim"
    )

    val bgGradient = when {
        isCurrent -> Brush.horizontalGradient(listOf(Color(0xFF131A29), Color(0xFF0F2436)))
        isCompleted -> Brush.horizontalGradient(listOf(Color(0xFF131A29), Color(0xFF122822)))
        else -> Brush.horizontalGradient(listOf(Color(0xFF0E131F), Color(0xFF0E131F)))
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, borderColor, RoundedCornerShape(10.dp)),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(10.dp)
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .background(bgGradient)
                .padding(12.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // Step Indicator Badge
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .scale(if (isCurrent) pulseScale else 1.0f)
                        .clip(CircleShape)
                        .background(
                            when {
                                isCompleted -> Color(0xFF10B981)
                                isCurrent -> Color(0xFF00F2FE)
                                else -> Color(0xFF1E293B)
                            }
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    when {
                        isCompleted -> Icon(
                            Icons.Default.Check,
                            contentDescription = null,
                            tint = Color(0xFF0A0E17),
                            modifier = Modifier.size(18.dp)
                        )
                        isCurrent -> CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            strokeWidth = 2.dp,
                            color = Color(0xFF0A0E17)
                        )
                        else -> Text(
                            "$index",
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp,
                            color = Color(0xFF64748B)
                        )
                    }
                }

                Spacer(Modifier.width(12.dp))

                // Step Content
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            step.title,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = if (isCurrent || isCompleted) FontWeight.Bold else FontWeight.Medium,
                            color = when {
                                isCompleted -> Color(0xFF10B981)
                                isCurrent -> Color(0xFF00F2FE)
                                else -> Color(0xFF64748B)
                            }
                        )
                        if (isCompleted) {
                            Spacer(Modifier.width(6.dp))
                            Text("Done", fontSize = 10.sp, color = Color(0xFF10B981), fontWeight = FontWeight.Bold)
                        }
                    }

                    if (isCurrent) {
                        Spacer(Modifier.height(2.dp))
                        Text(
                            step.activeDescription,
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFFE2E8F0),
                            fontSize = 11.sp
                        )
                    }
                }

                // Step Icon
                Icon(
                    step.icon,
                    contentDescription = null,
                    tint = when {
                        isCompleted -> Color(0xFF10B981)
                        isCurrent -> Color(0xFF00F2FE)
                        else -> Color(0xFF334155)
                    },
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}
