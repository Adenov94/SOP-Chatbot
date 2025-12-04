import streamlit as st
import openai
from dotenv import load_dotenv
import os
from PyPDF2 import PdfReader
from docx import Document
import json
import graphviz

# Load environment variables
load_dotenv()

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Page configuration
st.set_page_config(
    page_title="AI Chatbot with SOP Analysis",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "You are a helpful AI assistant. Be concise, accurate, and professional in your responses."

if "sop_content" not in st.session_state:
    st.session_state.sop_content = None

if "sop_steps" not in st.session_state:
    st.session_state.sop_steps = []

# Sidebar navigation
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio(
    "Select Page",
    ["💬 Chatbot", "⚙️ System Prompt", "📄 SOP Analysis"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **About This App**
    
    - **Chatbot**: Interactive AI conversation
    - **System Prompt**: Configure AI behavior
    - **SOP Analysis**: Analyze and visualize SOPs
    """
)

# Function to extract text from PDF
def extract_text_from_pdf(file):
    try:
        pdf_reader = PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

# Function to extract text from DOCX
def extract_text_from_docx(file):
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return None

# Function to get ChatGPT response
def get_chatgpt_response(messages):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# Function to analyze SOP and extract steps
def analyze_sop(content):
    try:
        messages = [
            {"role": "system", "content": "You are an expert in analyzing Standard Operating Procedures (SOPs) and extracting process steps."},
            {"role": "user", "content": f"""Analyze the following SOP document and extract all the process steps. 
            Return the steps in a JSON format with the following structure:
            {{
                "steps": [
                    {{"id": "1", "title": "Step Name", "description": "Step description", "type": "process"}},
                    {{"id": "2", "title": "Decision Point", "description": "Decision description", "type": "decision"}},
                    ...
                ],
                "connections": [
                    {{"from": "1", "to": "2"}},
                    ...
                ]
            }}
            
            Use type "start" for the beginning, "process" for actions, "decision" for decision points, and "end" for the final step.
            
            SOP Document:
            {content[:4000]}"""}
        ]
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.3,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content
        # Try to parse JSON from the response
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        
        return json.loads(result.strip())
    except Exception as e:
        st.error(f"Error analyzing SOP: {str(e)}")
        return None

# Function to create flowchart
def create_flowchart(steps_data):
    try:
        graph = graphviz.Digraph(comment='SOP Flowchart')
        graph.attr(rankdir='TB', size='10,10')
        graph.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue', fontname='Arial')
        
        # Add nodes
        for step in steps_data.get("steps", []):
            step_id = str(step["id"])
            title = step["title"]
            step_type = step.get("type", "process")
            
            # Set shape and color based on type
            if step_type == "start":
                graph.node(step_id, title, shape='ellipse', fillcolor='lightgreen')
            elif step_type == "end":
                graph.node(step_id, title, shape='ellipse', fillcolor='lightcoral')
            elif step_type == "decision":
                graph.node(step_id, title, shape='diamond', fillcolor='lightyellow')
            else:
                graph.node(step_id, title, shape='box', fillcolor='lightblue')
        
        # Add edges
        for connection in steps_data.get("connections", []):
            from_node = str(connection["from"])
            to_node = str(connection["to"])
            label = connection.get("label", "")
            graph.edge(from_node, to_node, label=label)
        
        return graph
    except Exception as e:
        st.error(f"Error creating flowchart: {str(e)}")
        return None

# ==================== PAGE 1: CHATBOT ====================
if page == "💬 Chatbot":
    st.title("💬 AI Chatbot")
    st.markdown("Start a conversation with the AI assistant. Use the System Prompt page to customize its behavior.")
    
    # Clear chat button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Prepare messages for API call including system prompt
        api_messages = [
            {"role": "system", "content": st.session_state.system_prompt}
        ] + st.session_state.messages
        
        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_chatgpt_response(api_messages)
                st.markdown(response)
        
        # Add assistant response to chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# ==================== PAGE 2: SYSTEM PROMPT ====================
elif page == "⚙️ System Prompt":
    st.title("⚙️ System Prompt Configuration")
    st.markdown("Configure how the AI assistant should behave. The system prompt guides the AI's personality, tone, and expertise.")
    
    st.markdown("---")
    
    # Predefined templates
    st.subheader("📋 Quick Templates")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🤝 Professional Assistant", use_container_width=True):
            st.session_state.system_prompt = "You are a professional business assistant. Provide clear, concise, and accurate responses. Use formal language and maintain a helpful, respectful tone."
            st.rerun()
    
    with col2:
        if st.button("👨‍🏫 Technical Expert", use_container_width=True):
            st.session_state.system_prompt = "You are a technical expert with deep knowledge in programming, engineering, and technology. Provide detailed technical explanations with examples. Use precise terminology and suggest best practices."
            st.rerun()
    
    with col3:
        if st.button("🎨 Creative Writer", use_container_width=True):
            st.session_state.system_prompt = "You are a creative writer with a flair for storytelling. Use vivid language, engaging narratives, and creative expression. Help users craft compelling content."
            st.rerun()
    
    st.markdown("---")
    
    # Custom system prompt
    st.subheader("✏️ Custom System Prompt")
    new_prompt = st.text_area(
        "Enter your custom system prompt:",
        value=st.session_state.system_prompt,
        height=200,
        help="This prompt will guide the AI's behavior and responses throughout the conversation."
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 Save", use_container_width=True):
            st.session_state.system_prompt = new_prompt
            st.success("✅ System prompt saved successfully!")
            st.balloons()
    
    with col2:
        if st.button("🔄 Reset to Default", use_container_width=True):
            st.session_state.system_prompt = "You are a helpful AI assistant. Be concise, accurate, and professional in your responses."
            st.rerun()
    
    st.markdown("---")
    
    # Current active prompt display
    st.subheader("📌 Current Active Prompt")
    st.info(st.session_state.system_prompt)
    
    # Tips section
    with st.expander("💡 Tips for Writing Good System Prompts"):
        st.markdown("""
        **Effective system prompts should:**
        
        1. **Be Clear and Specific**: Clearly define the role and expertise
        2. **Set the Tone**: Specify formal, casual, technical, or creative tone
        3. **Define Constraints**: Mention any limitations or focus areas
        4. **Include Personality**: Give the AI a character or style
        5. **Add Guidelines**: Specify formatting preferences or response structure
        
        **Examples:**
        - "You are a patient teacher explaining concepts to beginners."
        - "You are a data scientist specializing in machine learning. Provide code examples and explain algorithms."
        - "You are a friendly customer support agent. Be empathetic and solution-focused."
        """)

# ==================== PAGE 3: SOP ANALYSIS ====================
elif page == "📄 SOP Analysis":
    st.title("📄 SOP Document Analysis & Flowchart")
    st.markdown("Upload your Standard Operating Procedure (SOP) document to analyze its content and generate a process flowchart.")
    
    # File upload
    st.subheader("📤 Upload SOP Document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'txt'],
        help="Upload your SOP document in PDF, DOCX, or TXT format"
    )
    
    if uploaded_file is not None:
        # Extract text based on file type
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        with st.spinner("Reading document..."):
            if file_type == 'pdf':
                content = extract_text_from_pdf(uploaded_file)
            elif file_type == 'docx':
                content = extract_text_from_docx(uploaded_file)
            elif file_type == 'txt':
                content = uploaded_file.read().decode('utf-8')
            else:
                st.error("Unsupported file type")
                content = None
        
        if content:
            st.session_state.sop_content = content
            st.success(f"✅ Document loaded successfully! ({len(content)} characters)")
            
            # Display document content
            with st.expander("📖 View Document Content"):
                st.text_area("Document Text", content, height=300, disabled=True)
            
            st.markdown("---")
            
            # Analyze SOP button
            st.subheader("🔍 Analyze SOP")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🚀 Analyze & Generate Flowchart", use_container_width=True, type="primary"):
                    with st.spinner("Analyzing SOP document and generating flowchart..."):
                        steps_data = analyze_sop(content)
                        
                        if steps_data:
                            st.session_state.sop_steps = steps_data
                            st.success("✅ Analysis complete!")
                            st.rerun()
            
            # Display analysis results
            if st.session_state.sop_steps:
                st.markdown("---")
                st.subheader("📊 Analysis Results")
                
                # Display steps
                with st.expander("📝 Process Steps", expanded=True):
                    steps = st.session_state.sop_steps.get("steps", [])
                    
                    for i, step in enumerate(steps, 1):
                        step_type = step.get("type", "process")
                        icon = "🟢" if step_type == "start" else "🔴" if step_type == "end" else "🔶" if step_type == "decision" else "📌"
                        
                        st.markdown(f"""
                        **{icon} Step {step['id']}: {step['title']}**
                        - *Type*: {step_type.title()}
                        - *Description*: {step.get('description', 'N/A')}
                        """)
                        
                        if i < len(steps):
                            st.markdown("---")
                
                # Generate and display flowchart
                st.markdown("---")
                st.subheader("🗺️ Process Flowchart")
                
                try:
                    flowchart = create_flowchart(st.session_state.sop_steps)
                    
                    if flowchart:
                        st.graphviz_chart(flowchart)
                        
                        # Download options
                        col1, col2 = st.columns(2)
                        with col1:
                            # Save flowchart as DOT file
                            dot_data = flowchart.source
                            st.download_button(
                                label="📥 Download Flowchart (DOT)",
                                data=dot_data,
                                file_name="sop_flowchart.dot",
                                mime="text/plain"
                            )
                        
                        with col2:
                            # Save steps as JSON
                            json_data = json.dumps(st.session_state.sop_steps, indent=2)
                            st.download_button(
                                label="📥 Download Steps (JSON)",
                                data=json_data,
                                file_name="sop_steps.json",
                                mime="application/json"
                            )
                    
                except Exception as e:
                    st.error(f"Error generating flowchart: {str(e)}")
    
    else:
        # Instructions when no file is uploaded
        st.info("👆 Please upload an SOP document to begin analysis.")
        
        with st.expander("ℹ️ How to use this feature"):
            st.markdown("""
            **Step-by-step guide:**
            
            1. **Upload Document**: Click the file uploader and select your SOP document (PDF, DOCX, or TXT)
            2. **View Content**: Expand the document content viewer to verify the text was extracted correctly
            3. **Analyze**: Click the "Analyze & Generate Flowchart" button
            4. **Review**: View the extracted process steps and their relationships
            5. **Visualize**: Check the automatically generated flowchart
            6. **Download**: Save the flowchart or steps data for future reference
            
            **Supported File Types:**
            - PDF (.pdf)
            - Word Document (.docx)
            - Text File (.txt)
            
            **Tips:**
            - Ensure your SOP document is well-structured with clear steps
            - The AI will identify process steps, decision points, and flow
            - Complex SOPs may take a moment to analyze
            """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center'>
        <small>Powered by OpenAI GPT-3.5-Turbo</small><br>
        <small>Built with Streamlit 🎈</small>
    </div>
    """,
    unsafe_allow_html=True
)