#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Dashboard App — DevSecOps Toolbox KPI Analyzer
Dashboard interactivo con filtros, drill-down y visualizaciones avanzadas

Usage:
    streamlit run streamlit_app.py

Version: 1.0.0
Author: Harold Adrian
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kpi_analyzer.analyzer import KPIAnalyzer
from kpi_analyzer.maturity_model import assess_maturity, get_level_name, get_level_color, MaturityLevel
from kpi_analyzer.benchmarks import get_benchmark_level, BenchmarkLevel

# Page config
st.set_page_config(
    page_title="KPI Dashboard — DevSecOps Toolbox",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3em;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5em;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stMetric {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_kpi_data(platform='all'):
    """Load KPI data with caching"""
    analyzer = KPIAnalyzer()
    platform_filter = None if platform == 'all' else platform
    results = analyzer.analyze_all_kpis(platform=platform_filter)
    return results

@st.cache_data(ttl=300)
def calculate_maturity(kpi_data):
    """Calculate maturity assessment"""
    kpi_values = {}
    for kpi in kpi_data.get('kpis', []):
        kpi_id = kpi.get('id')
        value = kpi.get('value')
        if kpi_id and value is not None:
            if kpi_id == "ec_001":
                kpi_values["deployment_frequency"] = value
            elif kpi_id == "ec_002":
                kpi_values["change_failure_rate"] = value
            elif kpi_id == "conf_001":
                kpi_values["mttr"] = value
            elif kpi_id == "conf_002":
                kpi_values["availability"] = value
            elif kpi_id == "seg_001":
                kpi_values["mfa_coverage"] = value
            elif kpi_id == "obs_001":
                kpi_values["monitoring_coverage"] = value
            elif kpi_id == "cump_001":
                kpi_values["policy_adherence"] = value
            elif kpi_id == "efic_001":
                kpi_values["resource_utilization"] = value
    
    return assess_maturity(kpi_values)

def create_maturity_gauge(maturity_level, maturity_score):
    """Create maturity level gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=maturity_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Nivel de Madurez: {get_level_name(MaturityLevel(maturity_level))}", 'font': {'size': 24}},
        delta={'reference': (maturity_level - 1) if maturity_level > 0 else 0, 'increasing': {'color': "green"}},
        gauge={
            'axis': {'range': [None, 5], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': get_level_color(MaturityLevel(maturity_level))},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 1], 'color': '#e74c3c'},
                {'range': [1, 2], 'color': '#e67e22'},
                {'range': [2, 3], 'color': '#f39c12'},
                {'range': [3, 4], 'color': '#f1c40f'},
                {'range': [4, 5], 'color': '#2ecc71'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': maturity_level
            }
        }
    ))
    
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=60, b=20))
    return fig

def create_dimension_radar(dimensions):
    """Create radar chart for dimensions"""
    dimension_names = []
    dimension_scores = []
    
    for dim_name, dim_data in dimensions.items():
        dimension_names.append(dim_name.replace('_', ' ').title())
        kpis = dim_data.get('kpis', [])
        if kpis:
            avg_score = sum(k.get('value', 0) or 0 for k in kpis) / len(kpis)
            dimension_scores.append(round(avg_score, 2))
        else:
            dimension_scores.append(0)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=dimension_scores,
        theta=dimension_names,
        fill='toself',
        name='Score Actual',
        line_color='#667eea',
        fillcolor='rgba(102, 126, 234, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(dimension_scores) * 1.2 if dimension_scores else 100]
            )
        ),
        showlegend=False,
        height=500,
        margin=dict(l=80, r=80, t=40, b=40)
    )
    
    return fig

def create_dimension_bar(dimensions):
    """Create bar chart for dimensions"""
    dimension_names = []
    dimension_scores = []
    dimension_colors = []
    
    color_map = {
        "entrega_continua": "#3498db",
        "confiabilidad": "#2ecc71",
        "seguridad": "#e74c3c",
        "observabilidad": "#f39c12",
        "cumplimiento": "#9b59b6",
        "eficiencia_operativa": "#1abc9c"
    }
    
    for dim_name, dim_data in dimensions.items():
        dimension_names.append(dim_name.replace('_', ' ').title())
        kpis = dim_data.get('kpis', [])
        if kpis:
            avg_score = sum(k.get('value', 0) or 0 for k in kpis) / len(kpis)
            dimension_scores.append(round(avg_score, 2))
        else:
            dimension_scores.append(0)
        dimension_colors.append(color_map.get(dim_name, "#95a5a6"))
    
    fig = go.Figure(data=[
        go.Bar(
            x=dimension_names,
            y=dimension_scores,
            marker_color=dimension_colors,
            text=dimension_scores,
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Scores Promedio por Dimensión",
        xaxis_title="Dimensión",
        yaxis_title="Score",
        height=400,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    
    return fig

def main():
    """Main Streamlit app"""
    
    # Header
    st.markdown('<h1 class="main-header">📊 KPI Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #6c757d; font-size: 1.2em;">DevSecOps Toolbox — Análisis de Métricas y Madurez</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        platform = st.selectbox(
            "Plataforma",
            options=['all', 'gcp', 'azdo', 'aws', 'terminal'],
            format_func=lambda x: x.upper() if x != 'all' else 'TODAS'
        )
        
        st.markdown("---")
        
        if st.button("🔄 Recargar Datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📚 Acerca de")
        st.markdown("""
        **KPI Analyzer v1.0.0**
        
        Sistema de análisis de KPIs DevSecOps con:
        - 30 KPIs en 6 dimensiones
        - Modelo de madurez 6 niveles
        - Benchmarks de industria
        - Análisis automático desde JSON
        """)
    
    # Load data
    with st.spinner("Cargando datos..."):
        kpi_data = load_kpi_data(platform)
        assessment = calculate_maturity(kpi_data)
    
    metadata = kpi_data.get('metadata', {})
    dimensions = kpi_data.get('dimensions', {})
    kpis = kpi_data.get('kpis', [])
    
    # Metadata row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📅 Generado", metadata.get('generated_at', 'N/A')[:10])
    
    with col2:
        st.metric("🌐 Plataforma", metadata.get('platform', 'all').upper())
    
    with col3:
        st.metric("📊 Total KPIs", len(kpis))
    
    with col4:
        st.metric("🎯 Nivel Madurez", f"{assessment.global_level}/5")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Madurez", "📈 Dimensiones", "📋 KPIs Detallados", "🚀 Roadmap"])
    
    with tab1:
        st.header("Evaluación de Madurez DevSecOps")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.plotly_chart(
                create_maturity_gauge(assessment.global_level, assessment.global_score),
                use_container_width=True
            )
        
        with col2:
            st.subheader("📊 Scores por Dimensión")
            for dim_name, dim_score in assessment.dimension_scores.items():
                st.metric(
                    dim_name.replace('_', ' ').title(),
                    f"{dim_score.score_percentage:.1f}%",
                    f"{dim_score.kpis_met}/{dim_score.kpis_total} KPIs cumplidos"
                )
        
        st.markdown("---")
        
        if assessment.recommended_actions:
            st.subheader("🚀 Acciones Recomendadas")
            for i, action in enumerate(assessment.recommended_actions[:5], 1):
                with st.expander(f"{i}. {action['action']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        impact_color = "🔴" if action['impact'] == "high" else "🟡" if action['impact'] == "medium" else "🟢"
                        st.write(f"**Impacto**: {impact_color} {action['impact'].upper()}")
                    with col2:
                        effort_color = "🔴" if action['effort'] == "high" else "🟡" if action['effort'] == "medium" else "🟢"
                        st.write(f"**Esfuerzo**: {effort_color} {action['effort'].upper()}")
    
    with tab2:
        st.header("Análisis por Dimensiones")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.plotly_chart(create_dimension_radar(dimensions), use_container_width=True)
        
        with col2:
            st.plotly_chart(create_dimension_bar(dimensions), use_container_width=True)
        
        st.markdown("---")
        
        # Dimension selector
        selected_dimension = st.selectbox(
            "Seleccionar Dimensión para Detalle",
            options=list(dimensions.keys()),
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        if selected_dimension:
            dim_data = dimensions[selected_dimension]
            st.subheader(f"📊 {selected_dimension.replace('_', ' ').title()}")
            st.write(f"**Peso**: {dim_data.get('weight', 0) * 100:.0f}%")
            
            # KPIs table for selected dimension
            dim_kpis = dim_data.get('kpis', [])
            if dim_kpis:
                kpi_table_data = []
                for kpi in dim_kpis:
                    value = kpi.get('value')
                    value_str = f"{value:.2f}" if isinstance(value, (int, float)) and value is not None else "N/A"
                    
                    kpi_table_data.append({
                        "KPI": kpi.get('name', 'N/A'),
                        "Valor": f"{value_str} {kpi.get('unit', '')}",
                        "Benchmark Elite": kpi.get('benchmarks', {}).get('elite', 'N/A'),
                        "Frameworks": ', '.join(kpi.get('frameworks', []))
                    })
                
                st.dataframe(kpi_table_data, use_container_width=True)
    
    with tab3:
        st.header("Detalle de Todos los KPIs")
        
        # Framework filter
        all_frameworks = set()
        for kpi in kpis:
            all_frameworks.update(kpi.get('frameworks', []))
        
        selected_frameworks = st.multiselect(
            "Filtrar por Framework",
            options=sorted(list(all_frameworks)),
            default=sorted(list(all_frameworks))
        )
        
        # Filter KPIs
        filtered_kpis = [
            kpi for kpi in kpis
            if any(fw in kpi.get('frameworks', []) for fw in selected_frameworks)
        ]
        
        # Display KPIs
        for kpi in filtered_kpis:
            with st.expander(f"📊 {kpi.get('name', 'N/A')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    value = kpi.get('value')
                    value_str = f"{value:.2f}" if isinstance(value, (int, float)) and value is not None else "N/A"
                    st.metric("Valor Actual", f"{value_str} {kpi.get('unit', '')}")
                
                with col2:
                    benchmarks = kpi.get('benchmarks', {})
                    st.write("**Benchmarks**")
                    st.write(f"🟢 Elite: {benchmarks.get('elite', 'N/A')}")
                    st.write(f"🟡 High: {benchmarks.get('high', 'N/A')}")
                
                with col3:
                    st.write("**Frameworks**")
                    for fw in kpi.get('frameworks', []):
                        st.write(f"• {fw}")
    
    with tab4:
        st.header("Roadmap de Mejora")
        
        st.info(f"**Nivel Actual**: {get_level_name(assessment.global_level)} ({assessment.global_level}/5)")
        st.info(f"**Próximo Nivel**: {get_level_name(assessment.next_level)}")
        st.info(f"**Gap**: {assessment.gap_to_next:.1f}%")
        
        st.markdown("---")
        
        if assessment.recommended_actions:
            st.subheader("📋 Plan de Acción Priorizado")
            
            for i, action in enumerate(assessment.recommended_actions, 1):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{i}. {action['action']}**")
                
                with col2:
                    impact_emoji = "🔴" if action['impact'] == "high" else "🟡" if action['impact'] == "medium" else "🟢"
                    st.write(f"{impact_emoji} {action['impact'].title()}")
                
                with col3:
                    effort_emoji = "🔴" if action['effort'] == "high" else "🟡" if action['effort'] == "medium" else "🟢"
                    st.write(f"{effort_emoji} {action['effort'].title()}")
                
                st.markdown("---")
        else:
            st.success("🎉 ¡Felicitaciones! Has alcanzado el nivel máximo de madurez DevSecOps.")

if __name__ == "__main__":
    main()
