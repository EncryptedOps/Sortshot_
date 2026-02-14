import os
import json
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import threading
import time
from dotenv import load_dotenv
import re
import sys
import io

# Load environment variables from .env file
load_dotenv()

# Try to import Google's genai package
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
    print("✅ Using google.generativeai package")
except ImportError:
    GENAI_AVAILABLE = False
    print("❌ Google AI packages not installed. Run: pip install google-generativeai")

class ScreenshotRenamer:
    def __init__(self, root):
        self.root = root
        self.root.title("Sortshot")
        self.root.geometry("1000x750")
        
        # Configure style
        self.root.configure(bg='#f0f0f0')
        
        # Initialize status variables FIRST
        self.ai_status = tk.StringVar(value="AI: Initializing...")
        
        # Categories configuration
        self.categories = {
            'tickets': {'emoji': '🎫', 'color': '#FF6B6B', 'count': 1},
            'chats': {'emoji': '💬', 'color': '#4ECDC4', 'count': 1},
            'funny': {'emoji': '😂', 'color': '#FFE66D', 'count': 1},
            'movie': {'emoji': '🎬', 'color': '#95E1D3', 'count': 1},
            'others': {'emoji': '📁', 'color': '#A8E6CF', 'count': 1},
            'ai_smart': {'emoji': '🤖', 'color': '#9B59B6', 'count': 1}
        }
        
        # Variables
        self.source_folder = tk.StringVar()
        self.dest_folder = tk.StringVar()
        self.selected_files = []
        self.preview_images = []
        self.gemini_model = None
        self.ai_available = False
        self.category_counts = self.load_counts()
        
        # Initialize Gemini AI
        self.init_gemini()
        
        # Setup UI
        self.setup_ui()
        
        # Load existing config
        self.load_config()
        
    def init_gemini(self):
        """Initialize Google Gemini AI"""
        if not GENAI_AVAILABLE:
            self.ai_available = False
            self.ai_status.set("AI: ❌ Package not installed (pip install google-generativeai)")
            return
            
        try:
            # Get API key from environment variable
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key and api_key != "your_api_key_here":
                # Configure Gemini
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel('gemini-3-flash-preview')
                self.ai_available = True
                self.ai_status.set("AI: ✅ Connected to Gemini")
                print("✅ Gemini AI initialized successfully")
            else:
                self.ai_available = False
                self.ai_status.set("AI: ❌ No valid API Key (Add to .env file)")
                print("❌ No valid API key found in .env file")
        except Exception as e:
            self.ai_available = False
            self.ai_status.set(f"AI: ❌ Error - {str(e)[:30]}")
            print(f"❌ Gemini initialization error: {e}")
    
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Main Tab
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text='📸 Sortshot')
        
        # AI Tab
        ai_frame = ttk.Frame(notebook)
        notebook.add(ai_frame, text='🤖 AI Settings')
        
        # Settings Tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text='⚙️ Categories')
        
        # History Tab
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text='📜 History')
        
        self.setup_main_tab(main_frame)
        self.setup_ai_tab(ai_frame)
        self.setup_settings_tab(settings_frame)
        self.setup_history_tab(history_frame)
        
    def setup_main_tab(self, parent):
        # Top Frame - Folder Selection
        top_frame = tk.Frame(parent, bg='#f0f0f0')
        top_frame.pack(fill='x', padx=10, pady=10)
        
        # AI Status Bar
        status_frame = tk.Frame(top_frame, bg='#f0f0f0')
        status_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0,10))
        
        tk.Label(status_frame, textvariable=self.ai_status, 
                bg='#f0f0f0', font=('Arial', 9)).pack(side='left')
        
        # Source Folder
        tk.Label(top_frame, text="Source Folder:", bg='#f0f0f0', font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=5)
        tk.Entry(top_frame, textvariable=self.source_folder, width=50).grid(row=1, column=1, padx=5)
        tk.Button(top_frame, text="Browse", command=self.browse_source, bg='#4ECDC4').grid(row=1, column=2, padx=5)
        
        # Destination Folder
        tk.Label(top_frame, text="Destination:", bg='#f0f0f0', font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky='w', padx=5, pady=5)
        tk.Entry(top_frame, textvariable=self.dest_folder, width=50).grid(row=2, column=1, padx=5, pady=5)
        tk.Button(top_frame, text="Browse", command=self.browse_dest, bg='#FF6B6B').grid(row=2, column=2, padx=5, pady=5)
        
        # Buttons Frame
        button_frame = tk.Frame(top_frame, bg='#f0f0f0')
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        tk.Button(button_frame, text="📂 Load Screenshots", command=self.load_images, 
                 bg='#95E1D3', font=('Arial', 10, 'bold'), padx=20).pack(side='left', padx=5)
        
        # AI Quick Rename Button
        ai_button = tk.Button(button_frame, text="🤖 AI Smart Rename", command=self.ai_rename_selected,
                     bg='#9B59B6', fg='white', font=('Arial', 10, 'bold'), padx=20)
        ai_button.pack(side='left', padx=5)
        
        # Disable AI button if not available
        if not self.ai_available:
            ai_button.config(state='disabled')
        
        # Category Buttons Frame
        category_frame = tk.LabelFrame(parent, text="Categories", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        category_frame.pack(fill='x', padx=10, pady=5)
        
        # Create category buttons
        self.category_buttons = {}
        for i, (cat_name, cat_info) in enumerate(self.categories.items()):
            btn_text = f"{cat_info['emoji']} {cat_name.title()} (Next: {cat_name}_{cat_info['count']:03d})"
            btn = tk.Button(category_frame, text=btn_text, 
                          bg=cat_info['color'],
                          fg='black' if cat_name != 'ai_smart' else 'white',
                          command=lambda c=cat_name: self.rename_selected(c),
                          width=22, height=2)
            btn.grid(row=i//3, column=i%3, padx=5, pady=5)
            self.category_buttons[cat_name] = btn
        
        # Preview Frame with Scrollbar
        preview_label = tk.Label(parent, text="Preview Screenshots:", bg='#f0f0f0', font=('Arial', 10, 'bold'))
        preview_label.pack(anchor='w', padx=10)
        
        # Create canvas with scrollbar for thumbnails
        canvas_frame = tk.Frame(parent)
        canvas_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        scrollbar = tk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='white')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel for scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Bottom Frame with Stats
        bottom_frame = tk.Frame(parent, bg='#f0f0f0')
        bottom_frame.pack(fill='x', padx=10, pady=10)
        
        self.stats_label = tk.Label(bottom_frame, text="Ready", bg='#f0f0f0')
        self.stats_label.pack(side='left')
        
        # Select All Button
        tk.Button(bottom_frame, text="Select All", command=self.select_all, bg='#A8E6CF').pack(side='right', padx=5)
    
    def setup_ai_tab(self, parent):
        # API Key Setup
        api_frame = tk.LabelFrame(parent, text="AI Configuration", padx=10, pady=10)
        api_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(api_frame, text="Google Gemini API Key:", font=('Arial', 9, 'bold')).pack(anchor='w')
        
        # Show current API key status
        current_key = os.getenv('GEMINI_API_KEY', 'Not set')
        if current_key and current_key != "your_api_key_here":
            masked_key = current_key[:8] + '...' + current_key[-4:]
        else:
            masked_key = "Not set or invalid"
        
        key_status = tk.Label(api_frame, text=f"Current: {masked_key}", fg='blue')
        key_status.pack(anchor='w', pady=5)
        
        # Instructions
        instructions = tk.LabelFrame(parent, text="How to Get an API Key", padx=10, pady=10)
        instructions.pack(fill='x', padx=10, pady=10)
        
        steps = [
            "1. Go to https://aistudio.google.com/",
            "2. Sign in with your Google account",
            "3. Click 'Get API Key' in the left sidebar",
            "4. Create a new API key",
            "5. Copy the key (starts with 'AIza...')",
            "6. Add it to your .env file: GEMINI_API_KEY=your_key_here"
        ]
        
        for step in steps:
            tk.Label(instructions, text=step, anchor='w', justify='left').pack(anchor='w', pady=2)
        
        # AI Prompt Customization
        prompt_frame = tk.LabelFrame(parent, text="AI Prompt Customization", padx=10, pady=10)
        prompt_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(prompt_frame, text="Custom Prompt for AI (optional):", font=('Arial', 9, 'bold')).pack(anchor='w')
        
        self.ai_prompt = scrolledtext.ScrolledText(prompt_frame, height=8, width=70)
        self.ai_prompt.pack(pady=5, fill='both', expand=True)
        
        # Load default prompt
        default_prompt = """You are a filename generator. Look at this image and create a short, descriptive filename (3-5 words).

Rules:
- Use ONLY lowercase letters, numbers, and hyphens
- NO spaces, NO special characters
- Describe the MAIN subject of the image
- Be specific but concise
- DO NOT use words like "image", "photo", "picture", "screenshot"
- DO NOT add any explanations, just return the filename

Examples:
- For a cat photo: "sleeping-orange-cat"
- For a food photo: "homemade-pizza-slice"
- For a landscape: "sunset-mountain-lake"
- For a document: "quarterly-report-2024"
- For a meme: "distracted-boyfriend-meme"

Generate only the filename, nothing else:"""
        
        self.ai_prompt.insert('1.0', default_prompt)
        
        # Test button
        test_btn = tk.Button(prompt_frame, text="Test AI Connection", command=self.test_ai_connection,
                     bg='#9B59B6', fg='white')
        test_btn.pack(pady=5)
        
        if not self.ai_available:
            test_btn.config(state='disabled')
    
    def test_ai_connection(self):
        """Test if AI is working"""
        try:
            if self.gemini_model:
                response = self.gemini_model.generate_content("Say 'AI is working!' if you can read this. Reply with just that phrase.")
                messagebox.showinfo("AI Test", f"✅ AI Response: {response.text}")
            else:
                messagebox.showerror("AI Test", "❌ AI not initialized")
        except Exception as e:
            messagebox.showerror("AI Test", f"❌ Error: {str(e)}")
    
    def setup_settings_tab(self, parent):
        # Category Management
        cat_frame = tk.LabelFrame(parent, text="Category Settings", padx=10, pady=10)
        cat_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Instructions
        tk.Label(cat_frame, text="Edit categories (format: name,emoji,color):", 
                font=('Arial', 9)).pack(anchor='w')
        
        # Category editor
        self.cat_text = scrolledtext.ScrolledText(cat_frame, height=10, width=50)
        self.cat_text.pack(pady=5)
        
        # Load current categories
        self.load_categories_to_editor()
        
        # Buttons
        btn_frame = tk.Frame(cat_frame)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="Save Categories", command=self.save_categories, 
                 bg='#4ECDC4').pack(side='left', padx=5)
        tk.Button(btn_frame, text="Reset Default", command=self.reset_categories, 
                 bg='#FF6B6B').pack(side='left', padx=5)
        
        # Naming Convention
        naming_frame = tk.LabelFrame(parent, text="Naming Convention", padx=10, pady=10)
        naming_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(naming_frame, text="Standard: [Category]_[Number].png").pack(anchor='w')
        tk.Label(naming_frame, text="AI Mode: [AI-Description]_[Number].png").pack(anchor='w')
        tk.Label(naming_frame, text="Example: golden-retriever-play_001.png").pack(anchor='w')
    
    def setup_history_tab(self, parent):
        # History display
        self.history_text = scrolledtext.ScrolledText(parent, height=20, width=80)
        self.history_text.pack(padx=10, pady=10, fill='both', expand=True)
        
        # Clear history button
        tk.Button(parent, text="Clear History", command=self.clear_history, 
                 bg='#FF6B6B').pack(pady=5)
        
        # Load history
        self.load_history()
    
    def load_categories_to_editor(self):
        self.cat_text.delete('1.0', tk.END)
        for name, info in self.categories.items():
            self.cat_text.insert(tk.END, f"{name},{info['emoji']},{info['color']}\n")
    
    def save_categories(self):
        try:
            lines = self.cat_text.get('1.0', tk.END).strip().split('\n')
            new_categories = {}
            for line in lines:
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 3:
                        name = parts[0].strip()
                        emoji = parts[1].strip()
                        color = parts[2].strip()
                        new_categories[name] = {
                            'emoji': emoji,
                            'color': color,
                            'count': self.categories.get(name, {}).get('count', 1)
                        }
            
            if new_categories:
                self.categories = new_categories
                self.save_config()
                messagebox.showinfo("Success", "Categories saved! Please restart the app to see changes.")
            else:
                messagebox.showwarning("Warning", "No valid categories found!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save categories: {str(e)}")
    
    def reset_categories(self):
        self.categories = {
            'tickets': {'emoji': '🎫', 'color': '#FF6B6B', 'count': 1},
            'chats': {'emoji': '💬', 'color': '#4ECDC4', 'count': 1},
            'funny': {'emoji': '😂', 'color': '#FFE66D', 'count': 1},
            'movie': {'emoji': '🎬', 'color': '#95E1D3', 'count': 1},
            'others': {'emoji': '📁', 'color': '#A8E6CF', 'count': 1},
            'ai_smart': {'emoji': '🤖', 'color': '#9B59B6', 'count': 1}
        }
        self.load_categories_to_editor()
        self.save_config()
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_folder.set(folder)
    
    def browse_dest(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.dest_folder.set(folder)
    
    def load_images(self):
        if not self.source_folder.get():
            messagebox.showwarning("Warning", "Please select a source folder first!")
            return
        
        # Clear existing thumbnails
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.selected_files = []
        self.preview_images = []
        
        # Load image files
        valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
        files = []
        for file in os.listdir(self.source_folder.get()):
            if file.lower().endswith(valid_extensions):
                files.append(file)
        
        if not files:
            messagebox.showinfo("Info", "No images found in the selected folder!")
            return
        
        # Sort files
        files.sort()
        
        # Create thumbnails
        for i, file in enumerate(files[:20]):  # Limit to 20 files for performance
            file_path = os.path.join(self.source_folder.get(), file)
            self.create_thumbnail(file_path, file, i)
        
        self.stats_label.config(text=f"Loaded {len(files)} images (showing first 20)")
    
    def create_thumbnail(self, file_path, filename, index):
        try:
            # Open and resize image
            img = Image.open(file_path)
            img.thumbnail((150, 150))
            photo = ImageTk.PhotoImage(img)
            
            # Create frame for each image
            frame = tk.Frame(self.scrollable_frame, bg='white', relief='solid', borderwidth=1)
            frame.pack(side='left', padx=5, pady=5, anchor='n')
            
            # Checkbox
            var = tk.BooleanVar()
            chk = tk.Checkbutton(frame, variable=var, bg='white', 
                                command=lambda f=filename, v=var: self.toggle_selection(f, v))
            chk.pack()
            
            # Image
            label = tk.Label(frame, image=photo, bg='white')
            label.image = photo  # Keep a reference
            label.pack()
            
            # Filename
            tk.Label(frame, text=filename[:15] + "..." if len(filename) > 15 else filename, 
                    bg='white', wraplength=140).pack()
            
            # Store reference
            self.preview_images.append({
                'frame': frame,
                'var': var,
                'filename': filename,
                'path': file_path
            })
            
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    
    def toggle_selection(self, filename, var):
        if var.get():
            if filename not in self.selected_files:
                self.selected_files.append(filename)
        else:
            if filename in self.selected_files:
                self.selected_files.remove(filename)
        
        self.stats_label.config(text=f"Selected: {len(self.selected_files)} files")
    
    def select_all(self):
        if not self.preview_images:
            return
            
        # Check if all are selected
        all_selected = all(item['var'].get() for item in self.preview_images)
        select = not all_selected  # Toggle
        
        self.selected_files = []
        for item in self.preview_images:
            item['var'].set(select)
            if select:
                self.selected_files.append(item['filename'])
        
        self.stats_label.config(text=f"Selected: {len(self.selected_files)} files")
    
    def rename_selected(self, category):
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select files to rename!")
            return
        
        if not self.dest_folder.get():
            messagebox.showwarning("Warning", "Please select a destination folder!")
            return
        
        # Create category subfolder if it doesn't exist
        cat_folder = os.path.join(self.dest_folder.get(), category)
        os.makedirs(cat_folder, exist_ok=True)
        
        # Get starting number
        start_num = self.categories[category]['count']
        
        # Rename and move files
        renamed_files = []
        for i, filename in enumerate(self.selected_files):
            # Generate new filename
            new_filename = f"{category}_{start_num + i:03d}.png"
            new_path = os.path.join(cat_folder, new_filename)
            
            # Copy and rename file
            src_path = os.path.join(self.source_folder.get(), filename)
            try:
                shutil.copy2(src_path, new_path)
                renamed_files.append(f"{filename} → {category}/{new_filename}")
            except Exception as e:
                renamed_files.append(f"Error with {filename}: {str(e)}")
        
        # Update category count
        self.categories[category]['count'] = start_num + len(self.selected_files)
        
        # Save to history
        self.save_to_history(category, renamed_files)
        
        # Update button text
        btn_text = f"{self.categories[category]['emoji']} {category.title()} (Next: {category}_{self.categories[category]['count']:03d})"
        self.category_buttons[category].config(text=btn_text)
        
        # Save counts
        self.save_counts()
        
        # Clear selection
        self.select_all()
        self.selected_files = []
        
        messagebox.showinfo("Success", f"Renamed {len(renamed_files)} files to {category} folder!")
    
    def ai_rename_selected(self):
        """Rename selected files using AI-generated descriptions"""
        if not self.ai_available:
            messagebox.showerror("AI Not Available", 
                               "AI is not configured. Please add your Gemini API key to the .env file.")
            return
        
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select files to rename!")
            return
        
        if not self.dest_folder.get():
            messagebox.showwarning("Warning", "Please select a destination folder!")
            return
        
        # Create AI folder
        ai_folder = os.path.join(self.dest_folder.get(), "ai_renamed")
        os.makedirs(ai_folder, exist_ok=True)
        
        # Get prompt from AI settings tab
        prompt_text = self.ai_prompt.get('1.0', tk.END).strip()
        if not prompt_text:
            prompt_text = "Generate a descriptive filename (3-5 words, use hyphens) for this image."
        
        # Progress window
        progress_win = tk.Toplevel(self.root)
        progress_win.title("AI Processing")
        progress_win.geometry("500x250")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        tk.Label(progress_win, text="🤖 AI is analyzing your images...", 
                font=('Arial', 12, 'bold')).pack(pady=10)
        tk.Label(progress_win, text="This may take a few seconds per image", 
                font=('Arial', 9)).pack()
        
        progress_bar = ttk.Progressbar(progress_win, length=400, mode='determinate')
        progress_bar.pack(pady=10)
        
        current_file_label = tk.Label(progress_win, text="", font=('Arial', 9), 
                                    wraplength=450, fg='blue')
        current_file_label.pack(pady=5)
        
        status_label = tk.Label(progress_win, text="Starting...", font=('Arial', 9))
        status_label.pack(pady=5)
        
        # Process in background thread
        def process_with_ai():
            renamed_files = []
            total = len(self.selected_files)
            failed_count = 0
            
            for i, filename in enumerate(self.selected_files):
                try:
                    # Update progress
                    progress_value = (i / total) * 100
                    progress_win.after(0, progress_bar.config, {'value': progress_value})
                    progress_win.after(0, current_file_label.config, 
                                     {'text': f"📷 Analyzing: {filename}"})
                    progress_win.after(0, status_label.config, 
                                     {'text': f"Processing {i+1} of {total}..."})
                    progress_win.after(0, progress_win.update)
                    
                    # Get full path
                    src_path = os.path.join(self.source_folder.get(), filename)
                    
                    # Generate AI description
                    ai_name = self.generate_ai_filename(src_path, prompt_text)
                    
                    # Create new filename with counter
                    new_filename = f"{ai_name}_{self.categories['ai_smart']['count']:03d}.png"
                    new_path = os.path.join(ai_folder, new_filename)
                    
                    # Copy and rename file
                    shutil.copy2(src_path, new_path)
                    renamed_files.append(f"{filename} → {new_filename}")
                    
                    # Increment counter
                    self.categories['ai_smart']['count'] += 1
                    
                    # Small delay to show progress
                    time.sleep(0.2)
                    
                except Exception as e:
                    failed_count += 1
                    renamed_files.append(f"❌ {filename}: Error - {str(e)[:50]}")
            
            # Update UI in main thread
            progress_win.after(0, progress_bar.config, {'value': 100})
            progress_win.after(0, current_file_label.config, {'text': ""})
            progress_win.after(0, status_label.config, 
                             {'text': f"✅ Complete! {total-failed_count} successful, {failed_count} failed"})
            
            # Save to history
            self.save_to_history("ai_smart", renamed_files)
            
            # Update AI button text
            btn_text = f"🤖 AI Smart (Next: ai_{self.categories['ai_smart']['count']:03d})"
            self.category_buttons['ai_smart'].config(text=btn_text)
            
            # Save counts
            self.save_counts()
            
            # Close progress window after 2 seconds
            progress_win.after(2000, progress_win.destroy)
            
            # Show summary
            messagebox.showinfo("AI Rename Complete", 
                              f"✅ Successfully renamed: {total-failed_count} files\n"
                              f"❌ Failed: {failed_count} files\n"
                              f"📁 Location: {ai_folder}")
        
        # Start processing thread
        thread = threading.Thread(target=process_with_ai)
        thread.daemon = True
        thread.start()
    
    def generate_ai_filename(self, image_path, prompt):
        """Generate filename using Gemini AI"""
        try:
            from PIL import Image as PILImage
            
            # Open image
            img = PILImage.open(image_path)
            
            # Use the custom prompt or default
            enhanced_prompt = prompt if prompt else """You are a filename generator. Look at this image and create a short, descriptive filename (3-5 words).

Rules:
- Use ONLY lowercase letters, numbers, and hyphens
- NO spaces, NO special characters
- Describe the MAIN subject of the image
- Be specific but concise
- DO NOT use words like "image", "photo", "picture"
- DO NOT add any explanations, just return the filename

Generate only the filename:"""
            
            # Generate content using Gemini
            response = self.gemini_model.generate_content([enhanced_prompt, img])
            ai_text = response.text.strip().lower()
            
            print(f"AI Raw Response: {ai_text}")  # Debug output
            
            # Clean the text thoroughly
            # Remove any markdown, quotes, or extra text
            ai_text = re.sub(r'[`*_#]', '', ai_text)  # Remove markdown
            ai_text = re.sub(r'["\'()]', '', ai_text)  # Remove quotes and parentheses
            
            # Take only the first line
            ai_text = ai_text.split('\n')[0]
            
            # Replace spaces and invalid characters with hyphens
            ai_text = re.sub(r'[^\w\s-]', '', ai_text)  # Remove special chars
            ai_text = re.sub(r'[-\s]+', '-', ai_text)   # Replace spaces/hyphens with single hyphen
            ai_text = ai_text.strip('-')                 # Remove leading/trailing hyphens
            
            # Remove common unwanted words
            unwanted = ['image', 'photo', 'picture', 'png', 'jpg', 'jpeg', 'screenshot', 'img']
            for word in unwanted:
                ai_text = ai_text.replace(f'{word}-', '').replace(f'-{word}', '')
                if ai_text == word:
                    ai_text = ''
            
            # Limit length
            if len(ai_text) > 45:
                parts = ai_text.split('-')
                result = []
                current_len = 0
                for part in parts:
                    if current_len + len(part) + 1 <= 45:
                        result.append(part)
                        current_len += len(part) + 1
                    else:
                        break
                ai_text = '-'.join(result)
            
            # If we got a valid name, return it
            if ai_text and len(ai_text) >= 3:
                print(f"✅ Generated filename: {ai_text}")
                return ai_text
            
            # Fallback if cleaning resulted in empty string
            return f"image-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
        except Exception as e:
            print(f"❌ AI generation error: {e}")
            # Fallback to timestamp
            return f"image-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def save_to_history(self, category, renamed_files):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history_text.insert(tk.END, f"\n--- {timestamp} - Category: {category} ---\n")
        for file in renamed_files:
            self.history_text.insert(tk.END, f"{file}\n")
        self.history_text.see(tk.END)
        
        # Auto-save history to file
        self.save_history_to_file()
    
    def save_history_to_file(self):
        history_file = os.path.join(os.path.dirname(__file__), 'history.txt')
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write(self.history_text.get('1.0', tk.END))
        except:
            pass
    
    def load_history(self):
        history_file = os.path.join(os.path.dirname(__file__), 'history.txt')
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.history_text.insert(tk.END, f.read())
        except:
            pass
    
    def clear_history(self):
        if messagebox.askyesno("Confirm", "Clear all history?"):
            self.history_text.delete('1.0', tk.END)
            self.save_history_to_file()
    
    def save_counts(self):
        config = {
            'categories': self.categories,
            'last_source': self.source_folder.get(),
            'last_dest': self.dest_folder.get()
        }
        try:
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass
    
    def load_counts(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                # Update categories with saved counts
                if 'categories' in config:
                    for cat_name, cat_info in config['categories'].items():
                        if cat_name in self.categories:
                            self.categories[cat_name]['count'] = cat_info.get('count', 1)
                return config
        except:
            return {}
    
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.source_folder.set(config.get('last_source', ''))
                self.dest_folder.set(config.get('last_dest', ''))
        except:
            pass
    
    def save_config(self):
        config = {
            'categories': self.categories,
            'last_source': self.source_folder.get(),
            'last_dest': self.dest_folder.get()
        }
        try:
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass

def main():
    root = tk.Tk()
    app = ScreenshotRenamer(root)
    
    # Save config on close
    def on_closing():
        app.save_config()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()