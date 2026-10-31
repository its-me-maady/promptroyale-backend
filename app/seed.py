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
