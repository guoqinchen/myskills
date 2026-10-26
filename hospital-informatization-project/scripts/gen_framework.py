#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统架构图生成脚本（V3）
================================
支持两种运行模式：

模式A（默认，从模块列表生成）：
    python gen_framework.py --project "项目名" \
        --modules "360视图,处方审核,..." \
        --output "系统架构图.html" \
        --mermaid-output "系统架构图.mmd"

模式B（推荐，基于 mermaid 源码再渲染）：
    python gen_framework.py --project "项目名" \
        --render-mermaid \
        --mermaid-input "系统架构图.mmd" \
        --output "系统架构图.html"

特性：
1. 双输出：HTML 渲染产物 + Mermaid 源码文件（.mmd）
2. HTML 内嵌完整 mermaid 源码副本（注释块），保证可独立分发
3. 保留 ECharts 力导向图（组件关系拓扑视图）与 hover 详情弹窗
4. 兼容 V2 三栏静态布局（模式A 自动生成内置 mermaid 源码）
"""

import argparse
import os
import datetime


# ============================================================
# Mermaid 默认模板（医院信息化项目标准架构）
# ============================================================
DEFAULT_MERMAID = """%% 项目名称：{project_name}
%% 版本：v1.0
%% 生成日期：{today}
%% 设计依据：WS/T 826-2023、GB/T 22239-2019
%% 修改建议：直接编辑本文件后运行 gen_framework.py --render-mermaid 重新渲染
graph TB
    %% ===== 用户层 =====
    subgraph L5["用户层"]
        L5_OutPatient["门急诊药房"]
        L5_InPatient["住院药房"]
        L5_PIVAS["PIVAS"]
        L5_Doctor["医生工作站"]
        L5_Nurse["护士工作站"]
        L5_Mobile["移动平台"]
    end

    %% ===== 展现层 =====
    subgraph L4["展现层"]
        L4_Web["Web端"]
        L4_App["移动App"]
        L4_Report["统计报表"]
        L4_Dashboard["决策看板"]
    end

    %% ===== 功能应用层 =====
    subgraph L3["功能应用层"]
{app_nodes}
    end

    %% ===== 接口/数据处理层 =====
    subgraph L2["接口/数据处理层"]
        L2_Gateway["API网关"]
        L2_HL7["HL7 V2/V3"]
        L2_CDA["CDA文档"]
        L2_ICD["ICD-9/10"]
        L2_ETL["ETL同步"]
    end

    %% ===== 数据源层 =====
    subgraph L1_Data["数据源层"]
        D_EMR["EMR"]
        D_HIS["HIS"]
        D_LIS["LIS"]
        D_PACS["PACS/RIS"]
        D_CDSS["CDSS"]
    end

    %% ===== 基础设施层 =====
    subgraph L0["基础设施层"]
        I_Net["通信网络"]
        I_Server["服务器集群"]
        I_Storage["存储阵列"]
        I_VM["虚拟化平台"]
        I_CDR["CDR集成平台"]
    end

    %% ===== 数据流向 =====
    L5_OutPatient --> L4_Web
    L5_Doctor --> L4_Web
    L5_Mobile --> L4_App
    L4_Web --> L3_First
    L4_App --> L3_First
    L3_First --> L2_Gateway
    L2_Gateway --> D_EMR
    L2_Gateway --> D_HIS
    L2_ETL --> I_CDR
    D_EMR --> I_Server
    D_HIS --> I_Server

    %% ===== 样式定义 =====
    classDef userLayer fill:#c8e6c9,stroke:#43a047,stroke-width:2px,color:#1b5e20
    classDef presentLayer fill:#fff8f0,stroke:#fb8c00,stroke-width:2px,color:#e65100
    classDef appLayer fill:#ffe0b2,stroke:#fb8c00,stroke-width:2px,color:#e65100
    classDef ifLayer fill:#fce4ec,stroke:#ec407a,stroke-width:2px,color:#ad1457
    classDef dataLayer fill:#f3e5f5,stroke:#ab47bc,stroke-width:2px,color:#4a148c
    classDef infraLayer fill:#ffcdd2,stroke:#e53935,stroke-width:2px,color:#b71c1c

    class L5_OutPatient,L5_InPatient,L5_PIVAS,L5_Doctor,L5_Nurse,L5_Mobile userLayer
    class L4_Web,L4_App,L4_Report,L4_Dashboard presentLayer
    class {app_class_list} appLayer
    class L2_Gateway,L2_HL7,L2_CDA,L2_ICD,L2_ETL ifLayer
    class D_EMR,D_HIS,D_LIS,D_PACS,D_CDSS dataLayer
    class I_Net,I_Server,I_Storage,I_VM,I_CDR infraLayer
"""

DEFAULT_APP_MODULES = [
    "360视图", "处方点评", "处方审核", "医药通信",
    "不良反应", "用药咨询", "电子药历", "监测预警",
    "指南/处方集", "移动药师", "统计分析", "规则引擎",
]


# ============================================================
# 节点元信息（用于 hover/click 详情弹窗）
# ============================================================
MODULE_META = {
    # 功能应用层
    "360视图": {"desc": "全景患者视图，整合诊断、检验、用药等全维度信息"},
    "处方点评": {"desc": "基于指南/规则的智能点评与不合理用药识别"},
    "处方审核": {"desc": "实时拦截与前置审核，支持多级审批流"},
    "医药通信": {"desc": "医-药-患三方沟通渠道，支持消息推送与随访"},
    "不良反应": {"desc": "药品不良反应(ADE)监测、上报与分析预警"},
    "用药咨询": {"desc": "在线药学咨询与用药教育知识库服务"},
    "电子药历": {"desc": "结构化药物治疗记录(MTM)与监护路径追踪"},
    "监测预警": {"desc": "TDM血药浓度、药物相互作用实时监测预警"},
    "指南/处方集": {"desc": "临床指南库与机构处方集维护管理"},
    "移动药师": {"desc": "移动端药学查房、床旁审核与扫码核对"},
    "统计分析": {"desc": "多维度用药指标统计与质量改进报表"},
    "规则引擎": {"desc": "可配置业务规则引擎，支持低代码规则编排"},

    # 数据处理层
    "API网关": {"desc": "RESTful API网关，统一鉴权与限流管理"},
    "实时同步": {"desc": "增量/全量实时数据同步，支持CDC模式"},
    "数据采集": {"desc": "ETL抽取转换加载，多源异构数据清洗入库"},
    "HL7 V2/V3": {"desc": "HL7 V2.x/V3消息解析与接口适配"},
    "HL7 V2-3": {"desc": "HL7 V2.x/V3消息解析与接口适配"},
    "HL7 CDA": {"desc": "临床文档架构(CDA)文档生成与交换标准"},
    "CDA文档": {"desc": "临床文档架构(CDA)文档生成与交换标准"},
    "ICD-9/10": {"desc": "疾病编码映射与国际标准对齐"},
    "ETL同步": {"desc": "ETL抽取转换加载，多源异构数据清洗入库"},

    # 数据源层
    "EMR": {"desc": "电子病历系统 — 门诊/住院病历文书与医嘱数据"},
    "HIS": {"desc": "医院信息系统 — 收费、挂号、排班等基础数据"},
    "COPE": {"desc": "临床药学引擎 — 药品知识库与规则中心"},
    "LIS": {"desc": "实验室信息系统 — 检验结果与危急值数据"},
    "CDSS": {"desc": "临床决策支持系统 — 诊疗推荐与知识推理"},
    "PACS / RIS": {"desc": "影像存档与放射科信息系统 — 影像阅片"},
    "PACS/RIS": {"desc": "影像存档与放射科信息系统 — 影像阅片"},

    # 基础设施层
    "通信网络": {"desc": "内网隔离网络，符合等级保护2.0要求"},
    "服务器集群": {"desc": "应用服务器集群，支持高可用负载均衡"},
    "服务器": {"desc": "应用服务器集群，支持高可用负载均衡"},
    "虚拟化": {"desc": "VMware/KVM虚拟化平台，资源弹性调度"},
    "虚拟化平台": {"desc": "VMware/KVM虚拟化平台，资源弹性调度"},
    "API接口": {"desc": "RESTful API网关，统一鉴权与限流管理"},
    "存储阵列": {"desc": "SAN/NAS存储阵列，RAID冗余备份策略"},
    "存储": {"desc": "SAN/NAS存储阵列，RAID冗余备份策略"},
    "前置机": {"desc": "医保/药监前置机，满足数据上报合规要求"},
    "客户端": {"desc": "PC/Web/移动端多端适配客户端部署"},
    "CDR集成平台": {"desc": "临床数据仓库(CDR)，支撑BI与科研分析"},
}


# ============================================================
# 模式A：从模块列表生成 mermaid 源码
# ============================================================
def build_mermaid_from_modules(project_name, modules):
    """根据模块列表生成 mermaid 源码"""
    app_modules = modules if modules else DEFAULT_APP_MODULES

    # 生成应用层节点
    app_node_lines = []
    for i, m in enumerate(app_modules):
        # 节点ID：L3_序号（移除非字母数字字符）
        safe_id = "L3_" + "".join(c if c.isalnum() else "_" for c in m)
        app_node_lines.append('        {}["{}"]'.format(safe_id, m))
    app_nodes = "\n".join(app_node_lines)

    # 应用层 class 列表
    safe_ids = ["L3_" + "".join(c if c.isalnum() else "_" for c in m) for m in app_modules]
    app_class_list = ",".join(safe_ids)

    # 第一个应用层节点作为入口
    first_app_id = safe_ids[0] if safe_ids else "L3_View"

    today = datetime.date.today().isoformat()
    mermaid_src = DEFAULT_MERMAID.format(
        project_name=project_name,
        today=today,
        app_nodes=app_nodes,
        app_class_list=app_class_list,
    )

    # 替换数据流向中的 L3_First 占位
    mermaid_src = mermaid_src.replace("L3_First", first_app_id)

    return mermaid_src


def write_mermaid_file(mermaid_src, output_path):
    """保存 mermaid 源码到 .mmd 文件"""
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mermaid_src)
    print("Mermaid源码已生成: " + output_path)


# ============================================================
# HTML 渲染：将 mermaid 源码渲染为带交互增强的 HTML
# ============================================================
def render_html_from_mermaid(project_name, mermaid_src, output_path, module_meta=None):
    """基于 mermaid 源码生成 HTML（含 mermaid.js 渲染 + ECharts 增强 + hover 弹窗）"""
    if module_meta is None:
        module_meta = MODULE_META

    # 将 module_meta 序列化为 JS 对象
    meta_lines = []
    for k, v in module_meta.items():
        # 转义引号
        k_esc = k.replace('"', '\\"')
        desc_esc = v.get("desc", "").replace('"', '\\"').replace("\n", " ")
        meta_lines.append('        "{}":{{desc:"{}"}}'.format(k_esc, desc_esc))
    meta_js = ",\n".join(meta_lines)

    # mermaid 源码副本（HTML 注释块，用于追溯/再渲染）
    mermaid_escaped = mermaid_src.replace("-->", "--&gt;").replace("<", "&lt;").replace(">", "&gt;")

    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{project_name} 系统架构图</title>

<!-- ========== Mermaid 源码副本（便于追溯/再渲染，请勿删除）========== -->
<!--
========== MERMAID_SOURCE_START ==========
{mermaid_src}
========== MERMAID_SOURCE_END ==========
-->

<!-- ========== CSS 样式 ========== -->
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: "FangSong","仿宋","STFangsong",serif;
    background: #eef1f5;
    padding: 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
}}
.arch-title {{
    text-align:center;
    font-size:22px; font-weight:bold; color:#222;
    padding:12px 0 8px;
    letter-spacing:3px;
}}
.arch-meta {{
    text-align:center; font-size:12px; color:#888;
    margin-bottom:8px;
}}
.mermaid-container {{
    background:#fff;
    border:2px solid #333;
    padding:24px;
    border-radius:8px;
    width: 1280px;
    max-width: 100%;
    box-shadow: 0 2px 12px rgba(0,0,0,.08);
}}
.mermaid {{
    text-align:center;
    font-family: "FangSong","仿宋","STFangsong",serif;
}}
.mermaid svg {{
    max-width: 100% !important;
    height: auto !important;
}}
#relationChart {{
    width:100%; height:420px; margin-top:24px;
    border:1px solid #ddd; border-radius:8px;
    background:#fff;
}}
.footer-note {{
    text-align:center; font-size:11px; color:#888;
    padding:10px 0 4px;
    border-top:1px dashed #ccc; margin-top:12px;
    width: 1280px; max-width: 100%;
}}
#echart-tooltip {{
    display:none; position:fixed; z-index:9999;
    background:#1a1a2e; color:#eee; border-radius:8px;
    padding:14px 18px; font-size:13px;
    box-shadow:0 4px 20px rgba(0,0,0,.4); max-width:320px;
    pointer-events:none;
}}
</style>

<!-- ========== Mermaid.js 渲染引擎 ========== -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<!-- ========== ECharts 交互增强 ========== -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
</head>
<body>

<h1 class="arch-title">{project_name} 系统总体架构图</h1>
<p class="arch-meta">设计依据：WS/T 826-2023《医院信息化建设标准与规范》、GB/T 22239-2019《等级保护基本要求》 | 渲染模式：Mermaid + ECharts</p>

<div class="mermaid-container">
    <div class="mermaid">
{mermaid_src}
    </div>
</div>

<div id="relationChart"></div>

<p class="footer-note">
    本系统采用本地私有化部署架构 | 数据存储于院内服务器 |
    符合《医疗卫生机构网络安全管理办法》合规要求 |
    支持 HL7 V2/V3 CDA、ICD-9/10、WHO-ART 标准互操作 |
    Mermaid 源码见本 HTML 文件头注释块（MERMAID_SOURCE_START / END）
</p>

<div id="echart-tooltip"></div>

<script>
// 初始化 mermaid 渲染
mermaid.initialize({{
    startOnLoad: true,
    theme: 'default',
    flowchart: {{
        curve: 'basis',
        useMaxWidth: true,
        htmlLabels: true,
    }},
    securityLevel: 'loose',
}});

// 节点元信息（hover/click 详情弹窗内容）
const moduleMeta = {{
{meta_js}
}};

const tooltip = document.getElementById('echart-tooltip');

// hover 详情弹窗：监听 mermaid 渲染后的 SVG 节点
function bindMermaidHover() {{
    const nodes = document.querySelectorAll('.mermaid svg .node, .mermaid svg .cluster');
    nodes.forEach(function(node){{
        node.addEventListener('mouseenter', function(e){{
            const txt = (node.textContent || '').trim().split(/[\\s]+/)[0];
            const meta = moduleMeta[txt];
            if(!meta) return;
            tooltip.innerHTML =
                '<strong style="color:#64b5f6;font-size:14px;">'+txt+'</strong>'+
                '<br><br>'+meta.desc;
            tooltip.style.display = 'block';
            const rect = node.getBoundingClientRect();
            let tx = rect.right + 8;
            let ty = rect.top;
            if(tx + 320 > window.innerWidth) tx = rect.left - 330;
            if(ty + 200 > window.innerHeight) ty = window.innerHeight - 210;
            tooltip.style.left = tx + 'px';
            tooltip.style.top = ty + 'px';
        }});
        node.addEventListener('mouseleave', function(){{
            tooltip.style.display = 'none';
        }});
    }});
}}

// mermaid 渲染完成后绑定 hover
window.addEventListener('load', function(){{
    setTimeout(bindMermaidHover, 600);
}});

// ECharts：层级关系力导向图
const chartDom = document.getElementById('relationChart');
const myChart = echarts.init(chartDom);
const option = {{
    title: {{
        text: '系统组件关系拓扑',
        left:'center', top:8,
        textStyle:{{fontSize:16,color:'#333'}}
    }},
    tooltip:{{ trigger:'item', formatter:'{{b}}' }},
    animationDurationUpdate:800,
    animationEasingUpdate:'quarticOut',
    series:[{{
        type:'graph', layout:'force',
        data:[
            {{name:'用户层', category:0, symbolSize:48, symbol:'roundRect',
              itemStyle:{{color:'#66bb6a'}}}},
            {{name:'门急诊药房', category:0, symbolSize:30}},
            {{name:'医生工作站', category:0, symbolSize:30}},
            {{name:'护士工作站', category:0, symbolSize:30}},

            {{name:'展现层', category:1, symbolSize:46, symbol:'roundRect',
              itemStyle:{{color:'#ffa726'}}}},
            {{name:'Web端', category:1, symbolSize:28}},
            {{name:'移动App', category:1, symbolSize:28}},

            {{name:'功能应用', category:2, symbolSize:50, symbol:'roundRect',
              itemStyle:{{color:'#ffa726'}}}},
            {{name:'360视图', category:2, symbolSize:30}},
            {{name:'处方审核', category:2, symbolSize:30}},
            {{name:'电子药历', category:2, symbolSize:30}},
            {{name:'监测预警', category:2, symbolSize:30}},

            {{name:'接口/数据处理', category:3, symbolSize:46, symbol:'roundRect',
              itemStyle:{{color:'#ec407a'}}}},
            {{name:'API网关', category:3, symbolSize:28}},
            {{name:'HL7 CDA', category:3, symbolSize:28}},
            {{name:'ICD-10', category:3, symbolSize:28}},

            {{name:'数据源', category:4, symbolSize:46, symbol:'roundRect',
              itemStyle:{{color:'#ab47bc'}}}},
            {{name:'EMR', category:4, symbolSize:28}},
            {{name:'HIS', category:4, symbolSize:28}},
            {{name:'LIS', category:4, symbolSize:28}},
            {{name:'CDSS', category:4, symbolSize:28}},

            {{name:'基础设施', category:5, symbolSize:46, symbol:'roundRect',
              itemStyle:{{color:'#e53935'}}}},
            {{name:'服务器集群', category:5, symbolSize:26}},
            {{name:'API网关', category:5, symbolSize:26}},
            {{name:'CDR仓库', category:5, symbolSize:26}},
        ],
        categories:[
            {{name:'用户层'}}, {{name:'展现层'}}, {{name:'功能应用'}},
            {{name:'接口/数据处理'}}, {{name:'数据源'}}, {{name:'基础设施'}},
        ],
        links:[
            {{source:'门急诊药房', target:'展现层'}},
            {{source:'医生工作站', target:'展现层'}},
            {{source:'护士工作站', target:'展现层'}},
            {{source:'展现层', target:'功能应用'}},
            {{source:'功能应用', target:'360视图'}},
            {{source:'功能应用', target:'处方审核'}},
            {{source:'功能应用', target:'电子药历'}},
            {{source:'功能应用', target:'监测预警'}},
            {{source:'功能应用', target:'接口/数据处理'}},
            {{source:'接口/数据处理', target:'API网关'}},
            {{source:'接口/数据处理', target:'HL7 CDA'}},
            {{source:'接口/数据处理', target:'ICD-10'}},
            {{source:'接口/数据处理', target:'数据源'}},
            {{source:'数据源', target:'EMR'}},
            {{source:'数据源', target:'HIS'}},
            {{source:'数据源', target:'LIS'}},
            {{source:'数据源', target:'CDSS'}},
            {{source:'数据源', target:'基础设施'}},
            {{source:'基础设施', target:'服务器集群'}},
            {{source:'基础设施', target:'API网关'}},
            {{source:'基础设施', target:'CDR仓库'}},
        ],
        roam:true,
        draggable:true,
        force:{{ repulsion:260, edgeLength:[80,160], gravity:.15, friction:.6 }},
        label:{{ show:true, fontSize:11, formatter:'{{b}}' }},
        lineStyle:{{ color:'#bbb', width:1.5, curveness:.2 }},
        emphasis:{{ focus:'adjacentEdgeWeight', lineStyle:{{width:3,color:'#555'}} }},
        edgeSymbol:['circle','arrow'],
        edgeSymbolSize:[3,8],
        itemStyle:{{ borderColor:'#fff', borderWidth:1.5,
                    shadowBlur:8, shadowColor:'rgba(0,0,0,.15)' }},
    }}],
    legend:{{ bottom:8, data:['用户层','展现层','功能应用','接口/数据处理','数据源','基础设施'] }},
    color:['#66bb6a','#ffa726','#ffa726','#ec407a','#ab47bc','#e53935'],
}};
myChart.setOption(option);
window.addEventListener('resize', () => myChart.resize());
myChart.on('click', function(params){{
    const meta = moduleMeta[params.name];
    if(meta) alert(params.name + '\n\n' + meta.desc);
}});
</script>

</body>
</html>"""

    html_content = html_content.format(
        project_name=project_name,
        mermaid_src=mermaid_src,
        meta_js=meta_js,
    )

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("HTML渲染产物已生成: " + output_path)


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="系统架构图生成脚本 V3（支持 mermaid 源码 + HTML 双输出）"
    )
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--modules", default="",
                        help="功能应用层模块列表（逗号分隔），模式A使用")
    parser.add_argument("--output", required=True,
                        help="输出 HTML 路径")
    parser.add_argument("--mermaid-output", default="",
                        help="同时输出 mermaid 源码文件路径（.mmd），强烈建议指定")
    parser.add_argument("--render-mermaid", action="store_true",
                        help="启用 mermaid 渲染模式（模式B）：基于 --mermaid-input 源码渲染 HTML")
    parser.add_argument("--mermaid-input", default="",
                        help="输入的 mermaid 源码文件路径（模式B 必填）")

    args = parser.parse_args()

    if args.render_mermaid:
        # 模式B：基于 .mmd 渲染 HTML
        if not args.mermaid_input:
            parser.error("模式B（--render-mermaid）必须指定 --mermaid-input")
        if not os.path.exists(args.mermaid_input):
            parser.error("mermaid-input 文件不存在: " + args.mermaid_input)

        with open(args.mermaid_input, "r", encoding="utf-8") as f:
            mermaid_src = f.read()

        render_html_from_mermaid(args.project, mermaid_src, args.output)

        # 若未指定 mermaid-output，自动以 mermaid-input 同名输出
        if not args.mermaid_output:
            print("（提示：模式B未指定 --mermaid-output，仅生成HTML，mermaid源码沿用输入文件）")

    else:
        # 模式A：从模块列表生成
        modules = None
        if args.modules:
            modules = [m.strip() for m in args.modules.split(",") if m.strip()]

        mermaid_src = build_mermaid_from_modules(args.project, modules)

        # 自动推断 mermaid-output 路径（如未指定）
        mermaid_out = args.mermaid_output
        if not mermaid_out:
            base, _ = os.path.splitext(args.output)
            mermaid_out = base + ".mmd"
            print("（提示：未指定 --mermaid-output，自动使用: " + mermaid_out + "）")

        # 写 .mmd 源码
        write_mermaid_file(mermaid_src, mermaid_out)

        # 渲染 HTML
        render_html_from_mermaid(args.project, mermaid_src, args.output)


if __name__ == "__main__":
    main()
