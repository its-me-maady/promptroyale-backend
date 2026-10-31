import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    QuizAnswerSubmission,
    QuizQuestionOut,
    QuizQuestionReview,
    QuizStartResponse,
    QuizSubmitResponse,
)

# Active in-memory battles registry for live session scoring
# In PRD 5.11: "Results are not persisted as conversation history, quiz history or leaderboard data."
active_battles: dict[str, dict[str, Any]] = {}

PRESET_CS101_QUESTIONS = [
    {
        "question": "What is the primary characteristic of a binary tree node?",
        "options": ["It can have at most two children", "It must have at least three children", "It cannot store integer values", "It has no left child"],
        "correct_option": 0,
        "explanation": "By definition, each node in a binary tree has at most two children: the left child and right child.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Binary Trees Overview"
    },
    {
        "question": "Which data structure is fundamentally utilized by Breadth-First Search (BFS)?",
        "options": ["Stack (LIFO)", "Queue (FIFO)", "Priority Queue", "Hash Table"],
        "correct_option": 1,
        "explanation": "BFS systematically utilizes a Queue (FIFO) to visit nodes level-by-level from top to bottom.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Breadth-First Search (BFS) Traversal"
    },
    {
        "question": "What is the time complexity of Breadth-First Search on a tree with V vertices?",
        "options": ["O(log V)", "O(V^2)", "O(V)", "O(1)"],
        "correct_option": 2,
        "explanation": "BFS processes each vertex exactly once, resulting in an O(V) time complexity.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Breadth-First Search (BFS) Traversal"
    },
    {
        "question": "In which order does an Inorder traversal visit the nodes of a binary tree?",
        "options": ["Root, Left, Right", "Left, Root, Right", "Left, Right, Root", "Right, Root, Left"],
        "correct_option": 1,
        "explanation": "Inorder traversal visits the Left subtree first, then the Root node, and finally the Right subtree.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Depth-First Search (DFS) Traversal"
    },
    {
        "question": "What unique property is produced by the Inorder traversal of a Binary Search Tree (BST)?",
        "options": ["Values in reverse order", "Values in strictly sorted ascending order", "Randomly arranged keys", "Alternating odd and even values"],
        "correct_option": 1,
        "explanation": "Inorder traversal of any valid Binary Search Tree always outputs the node keys in non-decreasing sorted order.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Depth-First Search (DFS) Traversal"
    },
    {
        "question": "Which data structure is typically used for an iterative implementation of Depth-First Search?",
        "options": ["Queue", "Circular Buffer", "Stack (LIFO)", "Binary Heap"],
        "correct_option": 2,
        "explanation": "DFS explores deeply along each branch, making a Stack (or call stack recursion) the natural data structure.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Depth-First Search (DFS) Traversal"
    },
    {
        "question": "What is the memory complexity of representing a sparse graph with V vertices and E edges using adjacency lists?",
        "options": ["O(V * E)", "O(V^2)", "O(V + E)", "O(1)"],
        "correct_option": 2,
        "explanation": "Adjacency lists only store edges that actually exist, yielding O(V + E) space complexity.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Graph Representation & Shortest Paths"
    },
    {
        "question": "Which algorithm computes single-source shortest paths on non-negative weighted graphs?",
        "options": ["Dijkstra's Algorithm", "Binary Search", "Kruskal's MST Algorithm", "Kosaraju's Algorithm"],
        "correct_option": 0,
        "explanation": "Dijkstra's algorithm finds shortest paths from a single source on graphs with non-negative edge weights.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Graph Representation & Shortest Paths"
    },
    {
        "question": "What auxiliary data structure allows Dijkstra's algorithm to achieve O((V + E) log V) time complexity?",
        "options": ["Hash Set", "Min-Priority Queue (Min-Heap)", "Linked List", "Adjacency Matrix"],
        "correct_option": 1,
        "explanation": "Using a min-heap allows efficient O(log V) extraction of the minimum distance vertex.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Graph Representation & Shortest Paths"
    },
    {
        "question": "What is the guaranteed lookup time complexity in a balanced binary search tree with n nodes?",
        "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
        "correct_option": 1,
        "explanation": "Balanced binary search trees (such as AVL or Red-Black trees) maintain a height of O(log n), guaranteeing O(log n) lookups.",
        "citation": "Lecture 3 — Tree Traversals & Breadth-First Search: Binary Trees Overview"
    }
]

async def start_quiz_battle(subject_id: int, db: AsyncSession) -> QuizStartResponse:
    battle_id = str(uuid.uuid4())

    # Build exactly 10 questions
    questions_data = list(PRESET_CS101_QUESTIONS)
    
    # Store in memory for scoring
    active_battles[battle_id] = {
        "subject_id": subject_id,
        "questions": questions_data
    }

    client_questions = [
        QuizQuestionOut(
            id=idx,
            question=q["question"],
            options=q["options"],
            source_citation=q["citation"]
        )
        for idx, q in enumerate(questions_data)
    ]

    return QuizStartResponse(
        battle_id=battle_id,
        subject_code="CS101",
        subject_name="Data Structures & Algorithms",
        time_limit_seconds=60,
        questions=client_questions
    )

async def submit_quiz_battle(
    battle_id: str,
    answers: list[QuizAnswerSubmission],
    time_taken_seconds: int
) -> QuizSubmitResponse:
    battle = active_battles.get(battle_id)
    if not battle:
        # Fallback to standard grading if battle expired from memory
        questions = PRESET_CS101_QUESTIONS
    else:
        questions = battle["questions"]

    reviews = []
    score = 0

    user_answers_map = {a.question_id: a.selected_option for a in answers}

    for idx, q in enumerate(questions):
        selected = user_answers_map.get(idx, -1)
        is_correct = (selected == q["correct_option"])
        if is_correct:
            score += 1
        reviews.append(
            QuizQuestionReview(
                question_id=idx,
                question=q["question"],
                selected_option=selected,
                correct_option=q["correct_option"],
                explanation=q["explanation"],
                source_citation=q["citation"],
                is_correct=is_correct
            )
        )

    accuracy = (score / len(questions)) * 100.0

    return QuizSubmitResponse(
        score=score,
        total=len(questions),
        accuracy_percentage=round(accuracy, 1),
        time_taken_seconds=time_taken_seconds,
        review=reviews
    )
