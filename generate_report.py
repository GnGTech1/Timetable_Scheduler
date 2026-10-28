"""
Automated Comprehensive PDF Project Report Generator for AI Timetable Scheduler.
Complies with Deliverable #4:
- 6-10 Page Publication-Quality PDF Report using ReportLab.
- Complete sections:
  1. Problem Formulation (Variables, Domains, Hard & Soft Constraints)
  2. Algorithm Descriptions & Design Choices
  3. Cost Function & Penalty Structure
  4. Experimental Results & Comprehensive Comparative Analysis
  5. Limitations & Future Work
  6. Team Member Contributions
- Embeds High-Resolution Benchmark Figures & Formatted Metrics Tables.
"""
import os
import sys
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Adds running headers and footers with total page numbers."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 755, "B.Tech Second Year | AI-Based Timetable Scheduler Project Report")
            self.drawRightString(558, 755, "Course: Artificial Intelligence")
            self.setStrokeColor(colors.HexColor("#D0D7DE"))
            self.setLineWidth(0.5)
            self.line(54, 748, 558, 748)

        # Footer
        footer_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(558, 38, footer_text)
        self.drawString(54, 38, "Confidential - Academic Evaluation Report")
        self.setStrokeColor(colors.HexColor("#D0D7DE"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)

        self.restoreState()

def generate_pdf_report():
    base_dir = os.path.dirname(__file__)
    pdf_path = os.path.join(base_dir, "docs", "AI_Timetable_Scheduler_Report.pdf")
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#1F497D")
    accent_color = colors.HexColor("#2B5C8F")
    dark_neutral = colors.HexColor("#222222")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=0,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#555555"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=accent_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_neutral,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10.5,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=dark_neutral,
        alignment=1
    )

    story = []

    # =========================================================================
    # TITLE & METADATA
    # =========================================================================
    story.append(Paragraph("AI-Based Timetable Scheduler", title_style))
    story.append(Paragraph("Constraint Satisfaction & Metaheuristic Search in University Course Timetabling", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=2, spaceAfter=12))

    meta_data = [
        [Paragraph("<b>Course:</b> Artificial Intelligence", body_style), Paragraph("<b>Team Size:</b> 3 Students", body_style)],
        [Paragraph("<b>Class:</b> B.Tech, Second Year", body_style), Paragraph("<b>Duration:</b> 2 Weeks", body_style)],
        [Paragraph("<b>Evaluation:</b> 18 Marks (+12 Bonus) = 30 Marks", body_style), Paragraph("<b>Submission:</b> Code, PDF Report, Web Demo", body_style)]
    ]
    meta_table = Table(meta_data, colWidths=[250, 250])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F4F6F9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 1. PROBLEM FORMULATION
    # =========================================================================
    story.append(Paragraph("1. Problem Formulation as a CSP", h1_style))
    story.append(Paragraph(
        "University Course Timetabling is an NP-complete combinatorial optimization challenge requiring the placement of lectures and lab sessions into discrete rooms and timeslots without clashes. Formally, we model this problem as a Constraint Satisfaction Problem (CSP) defined by a triplet <b>(X, D, C)</b>:",
        body_style
    ))

    story.append(Paragraph("<b>1.1 Variables (X):</b>", h2_style))
    story.append(Paragraph(
        "Each variable <i>X<sub>i</sub> &isin; X</i> represents a required weekly teaching session for a specific academic class group. For theory courses, each weekly credit hour forms an independent 1-period variable. For laboratory courses, per confirmed requirements (S3 promoted to hard constraint), sessions are grouped into atomic 2-period contiguous blocks. Each variable is characterized by <code>(Class_Name, Subject_Code, Teacher_Name, Duration, Session_Type)</code>.",
        body_style
    ))

    story.append(Paragraph("<b>1.2 Domains (D):</b>", h2_style))
    story.append(Paragraph(
        "The domain <i>D(X<sub>i</sub>)</i> represents all valid placements <code>(Day, Period, Room)</code> for session <i>X<sub>i</sub></i>. To eliminate dead search branches before exploration begins, domains are unary-filtered:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Room Type Compatibility:</b> Laboratory sessions are strictly restricted to lab rooms; theory lectures are restricted to standard classrooms.", bullet_style))
    story.append(Paragraph("&bull; <b>Room Capacity Filtering:</b> Only rooms with <code>Capacity &ge; Class_Strength</code> are included in the domain.", bullet_style))
    story.append(Paragraph("&bull; <b>Lunch Break Clearance:</b> Candidate periods overlapping the class group's assigned lunch break slot are pre-filtered out.", bullet_style))
    story.append(Paragraph("&bull; <b>Teacher Availability:</b> Candidate slots overlapping known teacher unavailability are pre-filtered out.", bullet_style))
    story.append(Paragraph("&bull; <b>Day Boundary Clearance:</b> 2-period lab blocks cannot begin in the final period of the working day.", bullet_style))

    story.append(Paragraph("<b>1.3 Constraints (C):</b>", h2_style))
    story.append(Paragraph("We enforce nine mandatory Hard Constraints (H1–H9) and four Soft Constraints (S1, S2, S4, S5):", body_style))

    constraints_table_data = [
        [Paragraph("<b>Type</b>", table_header_style), Paragraph("<b>Constraint Name</b>", table_header_style), Paragraph("<b>Formal Definition & Implementation</b>", table_header_style)],
        [Paragraph("Hard (H1)", table_cell_style), Paragraph("Teacher Clash", table_cell_style), Paragraph("A teacher cannot be scheduled for multiple sessions at the same (Day, Period).", table_cell_style)],
        [Paragraph("Hard (H2)", table_cell_style), Paragraph("Class Clash", table_cell_style), Paragraph("A class group cannot attend multiple sessions at the same (Day, Period).", table_cell_style)],
        [Paragraph("Hard (H3)", table_cell_style), Paragraph("Room Clash", table_cell_style), Paragraph("A physical room cannot accommodate multiple sessions at the same (Day, Period).", table_cell_style)],
        [Paragraph("Hard (H4)", table_cell_style), Paragraph("Capacity Sufficiency", table_cell_style), Paragraph("Assigned room capacity must be greater than or equal to class enrollment strength.", table_cell_style)],
        [Paragraph("Hard (H5)", table_cell_style), Paragraph("Room Type Fidelity", table_cell_style), Paragraph("Lab courses must occupy dedicated labs; theory courses must occupy standard classrooms.", table_cell_style)],
        [Paragraph("Hard (H6)", table_cell_style), Paragraph("Teacher Availability", table_cell_style), Paragraph("Faculty can only be scheduled during their declared available weekly periods.", table_cell_style)],
        [Paragraph("Hard (H7)", table_cell_style), Paragraph("Curriculum Fulfillment", table_cell_style), Paragraph("Every subject receives exactly its prescribed weekly credit lecture and lab hours.", table_cell_style)],
        [Paragraph("Hard (H8)", table_cell_style), Paragraph("Max Teacher Load", table_cell_style), Paragraph("Total weekly assigned teaching hours cannot exceed the teacher's maximum load.", table_cell_style)],
        [Paragraph("Hard (H9)", table_cell_style), Paragraph("Lunch Break Slot", table_cell_style), Paragraph("Each class has an inviolable reserved lunch break; no classes scheduled then.", table_cell_style)],
        [Paragraph("Hard (S3)", table_cell_style), Paragraph("Consecutive Labs", table_cell_style), Paragraph("Lab sessions must occupy continuous periods on the same day in the same lab.", table_cell_style)],
        [Paragraph("Soft (S1)", table_cell_style), Paragraph("Minimize Class Gaps", table_cell_style), Paragraph("Penalize free periods (idle gaps) between a class's first and last daily lecture (+10 pts).", table_cell_style)],
        [Paragraph("Soft (S2)", table_cell_style), Paragraph("Subject Daily Spread", table_cell_style), Paragraph("Avoid duplicate theory lectures of the same subject on the same day (+15 pts).", table_cell_style)],
        [Paragraph("Soft (S4)", table_cell_style), Paragraph("Teacher Preferences", table_cell_style), Paragraph("Respect faculty scheduling preferences, e.g. avoiding Period 1 classes (+10 pts).", table_cell_style)],
        [Paragraph("Soft (S5)", table_cell_style), Paragraph("Teacher Fatigue", table_cell_style), Paragraph("Penalize more than 2 consecutive lecture periods for any faculty member (+15 pts).", table_cell_style)],
    ]
    c_table = Table(constraints_table_data, colWidths=[65, 120, 315])
    c_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FBFC")]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(c_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 2. COST FUNCTION
    # =========================================================================
    story.append(Paragraph("2. Objective & Cost Function Definition", h1_style))
    story.append(Paragraph(
        "To evaluate timetable quality across systematic and stochastic local search algorithms, we define a unified cost function following Section 5.1 of the assignment specification:",
        body_style
    ))
    story.append(Paragraph(
        "<b>Cost(A) = 1000 &times; N<sub>hard</sub>(A) + &sum; w<sub>i</sub> &times; N<sub>soft, i</sub>(A)</b>",
        ParagraphStyle('Formula', parent=body_style, fontName='Helvetica-Bold', fontSize=10.5, alignment=1, textColor=primary_color, spaceBefore=4, spaceAfter=6)
    ))
    story.append(Paragraph(
        "Here, <i>N<sub>hard</sub>(A)</i> represents the count of hard constraint clashes. A multiplier of 1,000 creates an unbridgeable barrier between feasible schedules (0 hard clashes) and infeasible states. The soft penalty weights are calibrated transparently: <i>w<sub>gap</sub> = 10</i>, <i>w<sub>clustering</sub> = 15</i>, <i>w<sub>pref</sub> = 10</i>, and <i>w<sub>fatigue</sub> = 15</i>.",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # 3. ALGORITHM IMPLEMENTATION & DESIGN CHOICES
    # =========================================================================
    story.append(Paragraph("3. Algorithm Implementations & Design Choices", h1_style))

    story.append(Paragraph("<b>3.1 Algorithm 1: Baseline Backtracking (Chronological DFS)</b>", h2_style))
    story.append(Paragraph(
        "The baseline systematic solver implements Depth-First Search with backtracking. Variables are processed in static chronological index order, and domain values are tested sequentially. Binary consistency (H1, H2, H3) is verified using O(1) slot occupancy lookup tables. The baseline contains no forward inference or variable heuristics. When tested on large instances with deep search trees, an execution timeout cleanly stops unpruned exponential exploration.",
        body_style
    ))

    story.append(Paragraph("<b>3.2 Algorithm 2: Heuristic Backtracking (MRV + Degree + Fast Forward Checking)</b>", h2_style))
    story.append(Paragraph(
        "To eliminate exponential thrashing, three foundational CSP heuristics were implemented:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Minimum Remaining Values (MRV):</b> Selects the unassigned variable with the fewest remaining legal domain values. Prioritizes 2-period lab blocks which have smaller domains and higher placement rigidity.", bullet_style))
    story.append(Paragraph("&bull; <b>Degree Heuristic:</b> Acts as an intelligent tie-breaker for MRV, selecting the variable involved in the greatest number of constraints with other unassigned variables (highest shared class and faculty edges).", bullet_style))
    story.append(Paragraph("&bull; <b>Forward Checking (FC):</b> When variable <i>X</i> is assigned placement <i>v</i>, FC immediately checks neighboring unassigned variables. If any neighbor's domain is reduced to zero legal placements (domain wipeout), the algorithm immediately prunes the branch and backtracks without wasting recursive steps.", bullet_style))

    story.append(Paragraph("<b>3.3 Algorithm 3: Min-Conflicts Local Search</b>", h2_style))
    story.append(Paragraph(
        "Min-Conflicts operates on complete assignments. Key algorithmic decisions include:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Initial Assignment:</b> Greedily initializes all sessions from unary-valid domains to minimize starting conflicts.", bullet_style))
    story.append(Paragraph("&bull; <b>Conflicted Variable Selection:</b> Detects all sessions currently involved in faculty, class, or room clashes, and randomly selects one conflicted session.", bullet_style))
    story.append(Paragraph("&bull; <b>Value Selection & Tie-Breaking:</b> Evaluates candidate domain values using O(1) clash delta counters; randomly breaks ties among minimal-clash values.", bullet_style))
    story.append(Paragraph("&bull; <b>Plateau Escape:</b> Implements a random walk with probability <i>p = 0.08</i> (reassigning to a random domain value) and random restarts if a local minimum persists.", bullet_style))

    story.append(Paragraph("<b>3.4 Bonus Algorithm 4: Simulated Annealing (+6 Marks)</b>", h2_style))
    story.append(Paragraph(
        "Simulated Annealing performs stochastic local search to minimize overall cost. At each iteration, two neighborhood moves are deployed: (1) single-session relocation to an alternate valid domain slot, and (2) pairwise placement swap between compatible sessions. Uphill moves (&Delta;E &gt; 0) are accepted with Metropolis probability <i>P = exp(-&Delta;E / T)</i> under an exponential cooling schedule <i>T<sub>k+1</sub> = &alpha; &times; T<sub>k</sub></i> (&alpha; = 0.995).",
        body_style
    ))

    story.append(Paragraph("<b>3.5 Bonus Algorithm 5: Hybrid CSP + Simulated Annealing (+6 Marks)</b>", h2_style))
    story.append(Paragraph(
        "The Hybrid architecture couples the mathematical correctness of systematic CSP with the continuous optimization power of metaheuristics. Stage 1 executes Heuristic Backtracking (or Min-Conflicts) to rapidly secure a strictly feasible solution (0 hard violations). Stage 2 launches Simulated Annealing initialized with this feasible state, applying soft penalties to compact class schedules and reduce teacher fatigue while rigorously penalizing hard clashes to preserve feasibility.",
        body_style
    ))

    story.append(Spacer(1, 10))

    # =========================================================================
    # 4. EXPERIMENTAL RESULTS & COMPARISON
    # =========================================================================
    story.append(Paragraph("4. Experimental Results and Comparative Analysis", h1_style))
    story.append(Paragraph(
        "All algorithms were rigorously evaluated on both the <b>Small Dataset</b> (3 classes, 6 teachers, 4 rooms, 54 sessions) and the <b>Large Dataset</b> (8 classes, 16 teachers, 10 rooms, 177 sessions). Randomized algorithms were executed over <b>10 independent runs</b> to compute exact averages and success rates.",
        body_style
    ))

    # Read and insert experimental results table
    exp_csv = os.path.join(base_dir, "data", "experimental_results.csv")
    if os.path.exists(exp_csv):
        df_exp = pd.read_csv(exp_csv)
        exp_table_data = [[
            Paragraph("<b>Dataset</b>", table_header_style),
            Paragraph("<b>Algorithm</b>", table_header_style),
            Paragraph("<b>Avg Time (s)</b>", table_header_style),
            Paragraph("<b>Nodes / Steps</b>", table_header_style),
            Paragraph("<b>Hard Clashes</b>", table_header_style),
            Paragraph("<b>Soft Penalty</b>", table_header_style),
            Paragraph("<b>Success Rate</b>", table_header_style),
        ]]
        for _, row in df_exp.iterrows():
            exp_table_data.append([
                Paragraph(str(row["Dataset"]), table_cell_style),
                Paragraph(str(row["Algorithm"]), table_cell_style),
                Paragraph(f"{row['Avg Time (s)']:.4f}" if isinstance(row['Avg Time (s)'], float) else str(row['Avg Time (s)']), table_cell_style),
                Paragraph(f"{row['Nodes / Iterations']:,.0f}" if isinstance(row['Nodes / Iterations'], (int, float)) else str(row['Nodes / Iterations']), table_cell_style),
                Paragraph(str(row["Hard Violations"]), table_cell_style),
                Paragraph(str(row["Soft Penalty Score"]), table_cell_style),
                Paragraph(str(row["Success Rate"]), table_cell_style),
            ])
        res_table = Table(exp_table_data, colWidths=[70, 130, 60, 75, 55, 60, 50])
        res_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FBFC")]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(res_table)

    story.append(PageBreak())

    # =========================================================================
    # EMBEDDED CONVERGENCE CHARTS
    # =========================================================================
    story.append(Paragraph("4.1 Convergence & Performance Visualizations", h1_style))

    fig_mc = os.path.join(base_dir, "docs", "figures", "cost_vs_iterations_min_conflicts.png")
    fig_sa = os.path.join(base_dir, "docs", "figures", "cost_vs_iterations_sa_hybrid.png")
    fig_bar = os.path.join(base_dir, "docs", "figures", "runtime_comparison_barchart.png")

    if os.path.exists(fig_mc):
        story.append(Image(fig_mc, width=460, height=190))
        story.append(Paragraph("<b>Figure 1:</b> Cost vs. Iterations convergence trajectory for Min-Conflicts Local Search.", ParagraphStyle('Caption', parent=body_style, fontSize=8, alignment=1, textColor=colors.HexColor("#555555"))))
        story.append(Spacer(1, 8))

    if os.path.exists(fig_bar):
        story.append(Image(fig_bar, width=460, height=185))
        story.append(Paragraph("<b>Figure 2:</b> Comparative runtime across algorithms on Small and Large datasets (logarithmic scale).", ParagraphStyle('Caption', parent=body_style, fontSize=8, alignment=1, textColor=colors.HexColor("#555555"))))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # =========================================================================
    # COMPARATIVE ANALYSIS (REQUIRED SECTION 6 QUESTIONS)
    # =========================================================================
    story.append(Paragraph("4.2 In-Depth Analytical Answers (Assignment Section 6)", h1_style))

    story.append(Paragraph("<b>Q1: Which method was faster?</b>", h2_style))
    story.append(Paragraph(
        "<b>Heuristic Backtracking (MRV + FC)</b> demonstrated the lowest raw computational latency on both datasets (0.0093s on Small; 0.1006s on Large). MRV's early pruning of constrained laboratory sessions and forward checking prevented futile deep dives. In local search, <b>Min-Conflicts</b> was remarkably rapid, resolving the Small dataset in an average of 15.4 iterations (0.0311s) and the Large dataset in 59.3 iterations (0.6662s). Baseline Backtracking expanded <b>6,274,841 nodes</b> on the large instance compared to only <b>4,608 nodes</b> for Heuristic CSP—a <b>1,361&times; reduction in search effort</b>.",
        body_style
    ))

    story.append(Paragraph("<b>Q2: Which gave better soft-constraint quality?</b>", h2_style))
    story.append(Paragraph(
        "The <b>Hybrid CSP + Simulated Annealing</b> architecture delivered superior soft-constraint quality (improving soft penalties down to 200 pts on Small and 1500 pts on Large) while maintaining a strict 100% feasibility rate (0 hard violations). Pure Backtracking algorithms stop immediately upon finding the first feasible branch, leaving soft constraints unoptimized. Standalone Simulated Annealing achieved low soft penalties but failed to consistently reach zero hard violations.",
        body_style
    ))

    story.append(Paragraph("<b>Q3: What happens as the problem grows?</b>", h2_style))
    story.append(Paragraph(
        "As the problem scaled from 54 sessions to 177 sessions, the search space expanded combinatorially (<i>D<sup>N</sup> &gt; 10<sup>150</sup></i>). Baseline Backtracking's node count exploded exponentially from 1,144 to 6.27 million nodes. In contrast, <b>Heuristic Backtracking</b> and <b>Min-Conflicts</b> exhibited polynomial scaling characteristics: Min-Conflicts required only 59 steps on the large problem, confirming the theoretical finding (Minton et al.) that Min-Conflicts scales nearly linearly on soluble instances under moderate constraint density.",
        body_style
    ))

    story.append(Paragraph("<b>Q4: When would you use each method?</b>", h2_style))
    story.append(Paragraph(
        "&bull; <b>Backtracking with Heuristics:</b> Ideal for strictly constrained, formal timetable generation where a mathematical guarantee of feasibility is mandatory.", bullet_style
    ))
    story.append(Paragraph(
        "&bull; <b>Min-Conflicts:</b> Ideal for interactive, real-time rescheduling (e.g. recovering from a teacher absence or room repair) where an existing timetable requires local repairs in milliseconds.", bullet_style
    ))
    story.append(Paragraph(
        "&bull; <b>Hybrid CSP + SA:</b> The optimal production choice for annual academic planning where schools demand both zero clashing (hard feasibility) and high ergonomic comfort (compact class days and minimized faculty fatigue).", bullet_style
    ))

    story.append(Spacer(1, 10))

    # =========================================================================
    # 5. LIMITATIONS & FUTURE WORK
    # =========================================================================
    story.append(Paragraph("5. Limitations and Future Work", h1_style))
    story.append(Paragraph(
        "<b>Limitations:</b> Currently, the system models faculty assignments as fixed class-subject mappings or automatic balanced pre-assignments. While this keeps domain dimensions compact, highly over-constrained institutions may benefit from dynamic multi-teacher co-teaching models. Additionally, cross-campus transit times were not explicitly factored into the room proximity model.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Future Work:</b> Planned enhancements include: (1) integrating Genetic Algorithms as an additional comparative benchmark, (2) incorporating classroom air conditioning and equipment requirements as secondary unary constraints, and (3) adding multi-campus travel buffer penalties.",
        body_style
    ))

    story.append(Spacer(1, 10))

    # =========================================================================
    # 6. TEAM MEMBER CONTRIBUTIONS
    # =========================================================================
    story.append(Paragraph("6. Team Member Contributions", h1_style))
    story.append(Paragraph("In accordance with team project guidelines (Team size: 3 students), responsibilities were partitioned:", body_style))

    team_table_data = [
        [Paragraph("<b>Student Name</b>", table_header_style), Paragraph("<b>Role / Focus Area</b>", table_header_style), Paragraph("<b>Key Responsibilities & Deliverables</b>", table_header_style)],
        [Paragraph("Team Member 1", table_cell_style), Paragraph("CSP & Heuristics Lead", table_cell_style), Paragraph("Problem formulation, Baseline Backtracking, MRV, Degree Heuristic, Forward Checking, Solvability Validator.", table_cell_style)],
        [Paragraph("Team Member 2", table_cell_style), Paragraph("Local Search & Bonus Lead", table_cell_style), Paragraph("Min-Conflicts local search, Simulated Annealing (+6), Hybrid CSP+SA (+6), Benchmarking experiments.", table_cell_style)],
        [Paragraph("Team Member 3", table_cell_style), Paragraph("Application & Report Lead", table_cell_style), Paragraph("Streamlit Web GUI, Timetable Grid views, Real-time Clash Inspector, Excel export, Report generation.", table_cell_style)],
    ]
    team_table = Table(team_table_data, colWidths=[90, 130, 280])
    team_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FBFC")]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(team_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"\n[OK] Comprehensive PDF report successfully compiled: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    generate_pdf_report()
