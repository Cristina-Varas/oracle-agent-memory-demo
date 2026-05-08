import streamlit as st

from memory_service import (
    CATEGORIES,
    MemoryServiceError,
    add_memory,
    chat_with_memory,
    delete_memory,
    get_memory_client,
    list_memories,
    search_memories,
)


st.set_page_config(
    page_title="Oracle Agent Memory",
    layout="wide",
)


def parse_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def show_error(exc: Exception) -> None:
    st.error(str(exc))


def render_memory(record: dict, *, show_delete: bool = False) -> None:
    with st.container(border=True):
        left, right = st.columns([0.72, 0.28], vertical_alignment="top")
        with left:
            st.subheader(record["title"])
            st.caption(
                " | ".join(
                    item
                    for item in [
                        record.get("category"),
                        record.get("customer_project"),
                        record.get("created_at"),
                    ]
                    if item
                )
            )
            if record.get("tags"):
                st.write(" ".join(f"`{tag}`" for tag in record["tags"]))
            st.write(record["content"])
            if record.get("source"):
                st.caption(f"Source: {record['source']}")
        with right:
            st.code(record["memory_id"], language=None)
            if show_delete and st.button(
                "Delete",
                key=f"delete_{record['memory_id']}",
                type="secondary",
            ):
                try:
                    delete_memory(record["memory_id"])
                    st.success("Memory deleted.")
                    st.rerun()
                except Exception as exc:
                    show_error(exc)


st.title("Oracle Agent Memory")
st.caption("A practical memory workspace backed by Autonomous Database and OCI Generative AI.")

try:
    get_memory_client()
except Exception as exc:
    st.error("The memory service could not start.")
    st.exception(exc)
    st.stop()

add_tab, search_tab, chat_tab, manage_tab = st.tabs(
    ["Add Memory", "Search Memories", "Chat with Memory", "Manage Memories"]
)

with add_tab:
    st.header("Add Memory")
    with st.form("add_memory_form", clear_on_submit=True):
        title = st.text_input("Title")
        category = st.selectbox("Category", CATEGORIES)
        customer_project = st.text_input("Customer / Project")
        tags_value = st.text_input("Tags", placeholder="renewal, exadata, follow-up")
        source = st.text_input("Source", placeholder="meeting, email, call, demo")
        content = st.text_area("Memory", height=180)
        submitted = st.form_submit_button("Add Memory", type="primary")

    if submitted:
        try:
            memory_id = add_memory(
                title=title,
                content=content,
                category=category,
                customer_project=customer_project,
                tags=parse_tags(tags_value),
                source=source,
            )
            st.success(f"Memory added: {memory_id}")
        except Exception as exc:
            show_error(exc)

with search_tab:
    st.header("Search Memories")
    with st.form("search_form"):
        query = st.text_input("Search query")
        col1, col2, col3 = st.columns([0.34, 0.33, 0.33])
        with col1:
            category_filter = st.selectbox("Category", ["Any"] + CATEGORIES)
        with col2:
            project_filter = st.text_input("Customer / Project filter")
        with col3:
            tag_filter = st.text_input("Tags filter", placeholder="tag1, tag2")
        limit = st.slider("Maximum results", min_value=1, max_value=25, value=10)
        searched = st.form_submit_button("Search", type="primary")

    if searched:
        try:
            results = search_memories(
                query,
                category=None if category_filter == "Any" else category_filter,
                customer_project=project_filter or None,
                tags=parse_tags(tag_filter),
                limit=limit,
            )
            st.caption(f"{len(results)} result(s)")
            for record in results:
                render_memory(record)
        except Exception as exc:
            show_error(exc)

with chat_tab:
    st.header("Chat with Memory")
    st.caption("Chat is read-only. It never creates or updates memories.")
    with st.form("chat_form"):
        question = st.text_area("Question", height=120)
        col1, col2 = st.columns(2)
        with col1:
            chat_category = st.selectbox("Category filter", ["Any"] + CATEGORIES)
        with col2:
            chat_project = st.text_input("Customer / Project filter", key="chat_project")
        asked = st.form_submit_button("Ask", type="primary")

    if asked:
        try:
            response = chat_with_memory(
                question,
                category=None if chat_category == "Any" else chat_category,
                customer_project=chat_project or None,
            )
            st.subheader("Answer")
            st.write(response["answer"])
            st.subheader("Sources")
            for record in response["sources"]:
                render_memory(record)
        except Exception as exc:
            show_error(exc)

with manage_tab:
    st.header("Manage Memories")
    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        list_limit = st.number_input("Rows", min_value=1, max_value=200, value=50, step=10)
    with col2:
        refresh = st.button("Refresh")

    try:
        records = list_memories(limit=int(list_limit))
        st.caption(f"{len(records)} memory record(s)")
        for record in records:
            render_memory(record, show_delete=True)
    except MemoryServiceError as exc:
        show_error(exc)
    except Exception as exc:
        show_error(exc)
