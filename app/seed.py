from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import get_password_hash
from app.database import AsyncSessionLocal
from app.models import (
    AIProviderCredential,
    BillingSnapshot,
    College,
    Department,
    Document,
    DocumentChunk,
    Subject,
    SubjectMembership,
    User,
)


async def seed_vaigai_college():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(College).where(College.domain == "vaigai.edu"))
        existing_college = result.scalar_one_or_none()
        if existing_college:
            return

        print("--> Auto-seeding initial database with Vaigai College academic data...")

        # 1. College
        college = College(
            name="Vaigai College of Engineering",
            domain="vaigai.edu",
            service_tier="Academic Enterprise"
        )
        session.add(college)
        await session.flush()

        # 2. Department
        dept = Department(
            college_id=college.id,
            name="Computer Science & Engineering",
            code="CSE"
        )
        session.add(dept)
        await session.flush()

        # 3. Subjects
        sub1 = Subject(
            department_id=dept.id,
            name="Data Structures & Algorithms",
            code="CS101",
            description="Fundamental data structures, search algorithms, tree traversals, and asymptotic complexity analysis."
        )
        sub2 = Subject(
            department_id=dept.id,
            name="Database Management Systems",
            code="CS202",
            description="Relational database design, relational algebra, SQL indexing, ACID properties, and query optimization."
        )
        session.add_all([sub1, sub2])
        await session.flush()

        # 4. Users
        password_hash = get_password_hash("Vaigai@123")

        student_adhithiyan = User(
            college_id=college.id,
            department_id=dept.id,
            email="adhithiyan@vaigai.edu",
            name="Adhithiyan",
            hashed_password=password_hash,
            role="student",
            status="active",
            is_active=True
        )

        faculty_user = User(
            college_id=college.id,
            department_id=dept.id,
            email="faculty.cse@vaigai.edu",
            name="Dr. K. Ramanathan",
            hashed_password=password_hash,
            role="department_user",
            status="active",
            is_active=True
        )

        admin_user = User(
            college_id=college.id,
            department_id=None,
            email="admin@vaigai.edu",
            name="Principal Office",
            hashed_password=password_hash,
            role="college_admin",
            status="active",
            is_active=True
        )

        session.add_all([student_adhithiyan, faculty_user, admin_user])
        await session.flush()

        # 5. Subject Membership: Adhithiyan enrolled in CS101 ONLY
        membership = SubjectMembership(
            student_id=student_adhithiyan.id,
            subject_id=sub1.id,
            status="active",
            is_active=True,
            added_at=datetime.now(UTC)
        )
        session.add(membership)

        # 6. Billing Snapshot
        billing = BillingSnapshot(
            college_id=college.id,
            snapshot_date=datetime.now(UTC).strftime("%Y-%m"),
            active_student_count=1,
            monthly_token_quota=1_000_000,
            tokens_consumed=142_500,
            tier="Academic Enterprise"
        )
        session.add(billing)

        # 7. AI Provider Credential
        cred = AIProviderCredential(
            student_id=student_adhithiyan.id,
            provider="gemini",
            encrypted_key="enc_gemini_token_placeholder",
            status="active"
        )
        session.add(cred)

        # 8. Pre-chunked Documents for CS101
        doc1 = Document(
            subject_id=sub1.id,
            title="Lecture 3 — Tree Traversals & Breadth-First Search",
            file_type="markdown",
            processing_status="available"
        )
        session.add(doc1)
        await session.flush()

        chunks_cs101 = [
            DocumentChunk(
                document_id=doc1.id,
                subject_id=sub1.id,
                chunk_index=1,
                section_title="Binary Trees Overview",
                content="A binary tree is a hierarchical data structure where each node has at most two children, referred to as the left child and right child. The top node is termed the root node. Balanced binary search trees guarantee O(log n) time complexity for lookup, insertion, and deletion operations."
            ),
            DocumentChunk(
                document_id=doc1.id,
                subject_id=sub1.id,
                chunk_index=2,
                section_title="Breadth-First Search (BFS) Traversal",
                content="Breadth-First Search (BFS) or level-order traversal visits nodes level by level from top to bottom and left to right. It systematically utilizes a Queue (FIFO) data structure. The algorithm begins by enqueuing the root node. While the queue is not empty, it dequeues the front node, processes it, and enqueues its non-null left and right children. The overall time complexity of BFS on a tree with V vertices is O(V)."
            ),
            DocumentChunk(
                document_id=doc1.id,
                subject_id=sub1.id,
                chunk_index=3,
                section_title="Depth-First Search (DFS) Traversal",
                content="Depth-First Search (DFS) explores as deep as possible along each branch before backtracking. Tree DFS traversals include Inorder (Left, Root, Right), Preorder (Root, Left, Right), and Postorder (Left, Right, Root). DFS is typically implemented using recursion or an explicit Stack (LIFO) data structure. Inorder traversal of a Binary Search Tree produces sorted values."
            ),
            DocumentChunk(
                document_id=doc1.id,
                subject_id=sub1.id,
                chunk_index=4,
                section_title="Graph Representation & Shortest Paths",
                content="Graphs can be represented using adjacency matrices or adjacency lists. For sparse graphs, adjacency lists are memory efficient O(V + E). Dijkstra's algorithm computes single-source shortest paths on non-negative weighted graphs in O((V + E) log V) using a priority queue (min-heap)."
            )
        ]
        session.add_all(chunks_cs101)

        # 9. Document for CS202
        doc2 = Document(
            subject_id=sub2.id,
            title="Lecture 1 — Relational Algebra Fundamentals",
            file_type="markdown",
            processing_status="available"
        )
        session.add(doc2)
        await session.flush()

        chunks_cs202 = [
            DocumentChunk(
                document_id=doc2.id,
                subject_id=sub2.id,
                chunk_index=1,
                section_title="Relational Algebra Operators",
                content="Relational algebra is a procedural query language. Fundamental operations comprise Selection (sigma), Projection (pi), Union (cup), Set Difference (-), Cartesian Product (times), and Rename (rho). Selection filters tuples based on predicate conditions, while Projection selects specified attributes."
            )
        ]
        session.add_all(chunks_cs202)

        await session.commit()
        print("--> Vaigai College successfully seeded with students, subjects, billing, and vetted syllabus!")


ACADEMIC_SUBJECTS_CATALOG = [
    {
        "dept_code": "CSE",
        "dept_name": "Computer Science & Engineering",
        "code": "CS302",
        "name": "Operating Systems",
        "description": "Process management, thread synchronization, memory virtualization, demand paging, and file systems.",
        "doc_title": "Lecture 4 — Virtual Memory & Paging Mechanisms",
        "chunks": [
            {
                "section": "Virtual Memory and Page Tables",
                "content": "Virtual memory abstracts physical RAM into contiguous address spaces per process. The Memory Management Unit (MMU) translates virtual addresses to physical frame numbers using page tables. Multilevel page tables reduce memory overhead for sparse address spaces."
            },
            {
                "section": "Page Replacement Algorithms",
                "content": "When page faults occur under high memory pressure, page replacement policies like Least Recently Used (LRU) and Clock algorithm determine which victim frames to evict to disk swap space."
            }
        ]
    },
    {
        "dept_code": "CSE",
        "dept_name": "Computer Science & Engineering",
        "code": "CS401",
        "name": "Computer Networks",
        "description": "Network layered architectures, packet switching, transport layer flow control, IP addressing, and routing algorithms.",
        "doc_title": "Lecture 2 — Transport Layer & TCP Congestion Control",
        "chunks": [
            {
                "section": "TCP Three-Way Handshake",
                "content": "Transmission Control Protocol (TCP) establishes reliable connections via SYN, SYN-ACK, and ACK sequence exchanges, guaranteeing in-order packet delivery."
            },
            {
                "section": "Congestion Control Mechanisms",
                "content": "TCP congestion avoidance employs Slow Start, Additive Increase Multiplicative Decrease (AIMD), and fast retransmit to prevent bufferbloat across network routers."
            }
        ]
    },
    {
        "dept_code": "CSE",
        "dept_name": "Computer Science & Engineering",
        "code": "CS405",
        "name": "Artificial Intelligence & Machine Learning",
        "description": "Search state spaces, heuristic reasoning, neural network architectures, loss functions, and transformer attention mechanisms.",
        "doc_title": "Lecture 5 — Transformer Self-Attention Architecture",
        "chunks": [
            {
                "section": "Scaled Dot-Product Attention",
                "content": "The transformer self-attention mechanism computes attention weights as Softmax((Q * K^T) / sqrt(d_k)) * V, allowing tokens to dynamically attend to contextual dependencies across arbitrary sequence lengths."
            },
            {
                "section": "Multi-Head Attention",
                "content": "Multi-head attention projects Queries, Keys, and Values into multiple lower-dimensional subspaces, enabling the model to jointly attend to information from different representation positions."
            }
        ]
    },
    {
        "dept_code": "ECE",
        "dept_name": "Electronics and Communication",
        "code": "EC201",
        "name": "Digital Electronics & Logic Design",
        "description": "Boolean algebra, combinational logic, sequential circuits, flip-flops, state machines, and FPGA basics.",
        "doc_title": "Lecture 1 — Combinational Logic & Karnaugh Maps",
        "chunks": [
            {
                "section": "K-Map Minimization",
                "content": "Karnaugh maps provide a graphical technique for minimizing Boolean algebraic expressions into optimal Sum-of-Products (SOP) forms, eliminating logic hazards and reducing gate count."
            },
            {
                "section": "Sequential Storage Elements",
                "content": "Flip-flops (D, JK, T) act as bistable multivibrators that store single binary bits synchronized to clock edge transitions."
            }
        ]
    },
    {
        "dept_code": "MECH",
        "dept_name": "Mechanical & Aerospace Engineering",
        "code": "ME201",
        "name": "Engineering Thermodynamics",
        "description": "Laws of thermodynamics, reversible cycles, entropy generation, pure substance state equations, and gas power cycles.",
        "doc_title": "Lecture 3 — Second Law of Thermodynamics & Entropy",
        "chunks": [
            {
                "section": "The Second Law of Thermodynamics",
                "content": "The Clausius and Kelvin-Planck statements dictate that heat cannot spontaneously flow from cold to hot bodies without external work. The Carnot cycle establishes the theoretical upper limit on thermal efficiency."
            },
            {
                "section": "Entropy and Irreversibility",
                "content": "Entropy measures unavailable energy and molecular disorder in isolated thermodynamic systems, always increasing during spontaneous real-world processes (dS >= 0)."
            }
        ]
    },
    {
        "dept_code": "IT",
        "dept_name": "Information Technology",
        "code": "IT201",
        "name": "Web Development & Cloud Architectures",
        "description": "Client-server models, RESTful APIs, distributed containerization, microservice communication, and serverless compute.",
        "doc_title": "Lecture 2 — Microservices & RESTful API Principles",
        "chunks": [
            {
                "section": "REST Architectural Constraints",
                "content": "Representational State Transfer enforces stateless interactions, uniform resource identifiers (URIs), standard HTTP verbs (GET, POST, PUT, DELETE), and JSON payload representations."
            },
            {
                "section": "Container Orchestration",
                "content": "Docker containers bundle applications with dependencies for reproducible deployment, managed by container engines for resilient horizontal scaling."
            }
        ]
    }
]


async def seed_academic_subjects():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(College).where(College.domain == "vaigai.edu"))
        college = res.scalar_one_or_none()
        if not college:
            return

        for item in ACADEMIC_SUBJECTS_CATALOG:
            # 1. Ensure department exists
            dept_res = await session.execute(
                select(Department).where(Department.code == item["dept_code"], Department.college_id == college.id)
            )
            dept = dept_res.scalars().first()
            if not dept:
                dept = Department(
                    college_id=college.id,
                    code=item["dept_code"],
                    name=item["dept_name"]
                )
                session.add(dept)
                await session.flush()

            # 2. Check if subject already exists
            sub_res = await session.execute(
                select(Subject).where(Subject.code == item["code"], Subject.department_id == dept.id)
            )
            sub = sub_res.scalars().first()
            if not sub:
                sub = Subject(
                    department_id=dept.id,
                    code=item["code"],
                    name=item["name"],
                    description=item["description"]
                )
                session.add(sub)
                await session.flush()

                # Add lecture document
                doc = Document(
                    subject_id=sub.id,
                    title=item["doc_title"],
                    file_type="markdown",
                    processing_status="available"
                )
                session.add(doc)
                await session.flush()

                # Add chunks
                for idx, ch in enumerate(item["chunks"], start=1):
                    chunk = DocumentChunk(
                        document_id=doc.id,
                        subject_id=sub.id,
                        chunk_index=idx,
                        section_title=ch["section"],
                        content=ch["content"]
                    )
                    session.add(chunk)

        await session.commit()
        print("--> Academic subjects and curriculum materials successfully seeded across departments!")
