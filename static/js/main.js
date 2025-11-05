class MarkdownLatexEditor {
    constructor() {
        this.editorElement = document.getElementById('editor');
        this.preview = document.getElementById('preview');
        this.modeSelector = document.getElementById('modeSelector');
        this.viewMode = document.getElementById('viewMode');
        this.aiModal = document.getElementById('aiModal');
        this.aiMessages = document.getElementById('aiMessages');
        this.aiQuestion = document.getElementById('aiQuestion');
        this.fullscreenBtn = document.getElementById('fullscreenBtn');

        this.currentMode = 'markdown';
        this.debounceTimer = null;
        this.cmEditor = null;

        this.init();
    }

    init() {
        this.initCodeMirror();
        this.setupEventListeners();
        this.loadFromLocalStorage();
        this.updatePreview();
        this.setupViewMode();
        this.updateStats();
    }

    initCodeMirror() {
        // Инициализация CodeMirror
        this.cmEditor = CodeMirror.fromTextArea(this.editorElement, {
            mode: 'markdown',
            theme: 'default',
            lineNumbers: true,
            lineWrapping: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            styleActiveLine: true,
            extraKeys: {
                "F11": function(cm) {
                    cm.setOption("fullScreen", !cm.getOption("fullScreen"));
                },
                "Esc": function(cm) {
                    if (cm.getOption("fullScreen")) cm.setOption("fullScreen", false);
                }
            }
        });

        // Обработчик изменений в редакторе
        this.cmEditor.on('change', () => {
            this.debounceUpdate();
            this.updateStats();
        });
    }

    setupEventListeners() {
        this.modeSelector.addEventListener('change', (e) => {
            // Сохраняем текущий контент перед сменой режима
            this.saveToLocalStorage();

            // Меняем режим
            this.currentMode = e.target.value;
            this.switchEditorMode();
            this.toggleToolbar();

            // Загружаем контент для нового режима
            this.loadFromLocalStorage();
            this.updatePreview();
        });

        this.viewMode.addEventListener('change', () => {
            this.setupViewMode();
        });

        this.fullscreenBtn.addEventListener('click', () => {
            this.toggleFullscreen();
        });

        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.insertText(e.target.dataset.insert);
            });
        });

        document.getElementById('exportHtml').addEventListener('click', () => {
            this.exportHTML();
        });

        document.getElementById('aiHelpBtn').addEventListener('click', () => {
            this.openAIModal();
        });

        document.getElementById('sendQuestion').addEventListener('click', () => {
            this.sendAIQuestion();
        });

        document.querySelector('.close').addEventListener('click', () => {
            this.closeAIModal();
        });

        window.addEventListener('click', (e) => {
            if (e.target === this.aiModal) {
                this.closeAIModal();
            }
        });

        this.aiQuestion.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendAIQuestion();
            }
        });

        document.getElementById('exportPdf').addEventListener('click', () => {
            this.exportPDF();
        });

        // Автосохранение каждые 30 секунд
        setInterval(() => {
            this.saveToServer();
            this.saveToLocalStorage();
        }, 30000);
    }

    switchEditorMode() {
        if (this.currentMode === 'markdown') {
            this.cmEditor.setOption('mode', {
                name: 'markdown',
                highlightFormatting: true
            });
        } else {
            this.cmEditor.setOption('mode', {
                name: 'stex',
                inMathMode: true
            });
        }
        // Обновляем редактор после смены режима
        setTimeout(() => {
            this.cmEditor.refresh();
        }, 100);
    }

    toggleToolbar() {
        const markdownTools = document.getElementById('markdownTools');
        const latexTools = document.getElementById('latexTools');

        if (this.currentMode === 'markdown') {
            markdownTools.style.display = 'flex';
            latexTools.style.display = 'none';
        } else {
            markdownTools.style.display = 'none';
            latexTools.style.display = 'flex';
        }
    }

    setupViewMode() {
    const editorPanel = document.getElementById('editorPanel');
    const previewPanel = document.getElementById('previewPanel');
    const viewMode = this.viewMode.value;

    // Сначала скрываем все
    editorPanel.style.display = 'none';
    previewPanel.style.display = 'none';

    // Показываем нужные панели
    if (viewMode === 'split' || viewMode === 'editor') {
        editorPanel.style.display = 'flex';
        editorPanel.style.flex = '1';
    }

    if (viewMode === 'split' || viewMode === 'preview') {
        previewPanel.style.display = 'flex';
        previewPanel.style.flex = '1';
    }

    // Принудительное обновление размеров CodeMirror
    setTimeout(() => {
        if (this.cmEditor) {
            this.cmEditor.refresh();
            // Дополнительное принудительное обновление
            const scroller = this.cmEditor.getScrollerElement();
            if (scroller) {
                scroller.style.height = '100%';
                scroller.style.minHeight = '100%';
            }
        }
    }, 50);
}

    insertText(text) {
        const doc = this.cmEditor.getDoc();
        const cursor = doc.getCursor();
        const selection = doc.getSelection();

        let newText;
        if (text.includes('\\n')) {
            newText = text.replace(/\\n/g, '\n');
        } else if (selection) {
            const parts = text.split(' ');
            newText = parts[0] + selection + (parts[1] || '');
        } else {
            newText = text;
        }

        doc.replaceSelection(newText);

        // Установка курсора после вставки
        if (!selection) {
            const newCursor = {
                line: cursor.line,
                ch: cursor.ch + newText.length
            };
            doc.setCursor(newCursor);
        }

        this.cmEditor.focus();
        this.updatePreview();
    }

    toggleFullscreen() {
        this.cmEditor.setOption("fullScreen", !this.cmEditor.getOption("fullScreen"));
    }

    debounceUpdate() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.updatePreview();
            this.saveToServer();
            this.saveToLocalStorage();
        }, 500);
    }

    updatePreview() {
        const content = this.cmEditor.getValue();

        fetch('/preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: content,
                mode: this.currentMode
            })
        })
        .then(response => response.json())
        .then(data => {
            this.preview.innerHTML = data.html;

            // Перерисовываем MathJax после обновления контента
            if (this.currentMode === 'latex' && window.MathJax) {
                MathJax.typesetPromise([this.preview]).catch(err => {
                    console.error('MathJax error:', err);
                });
            }
        })
        .catch(error => {
            console.error('Preview error:', error);
            this.preview.innerHTML = '<p>Ошибка при обновлении предпросмотра</p>';
        });
    }

    updateStats() {
        const content = this.cmEditor.getValue();
        const lineCount = this.cmEditor.lineCount();
        const charCount = content.length;

        document.getElementById('charCount').textContent = charCount;
        document.getElementById('lineCount').textContent = lineCount;
        // Обновляем индикатор режима
        document.getElementById('currentMode').textContent =
            this.currentMode === 'markdown' ? 'Markdown' : 'LaTeX';
    }

    saveToLocalStorage() {
        const content = this.cmEditor.getValue();
        const key = `editor-content-${this.currentMode}`;
        localStorage.setItem(key, content);
        console.log(`Сохранено в localStorage: ${key}`);
    }

    loadFromLocalStorage() {
        const key = `editor-content-${this.currentMode}`;
        const saved = localStorage.getItem(key);

        if (saved && this.cmEditor) {
            this.cmEditor.setValue(saved);
            console.log(`Загружено из localStorage: ${key}`);
        } else {
            // Устанавливаем начальный контент если ничего не сохранено
            const initialContent = this.getInitialContent();
            this.cmEditor.setValue(initialContent);
        }
        this.updateStats();
    }

    getInitialContent() {
        if (this.currentMode === 'markdown') {
            return `# Добро пожаловать в Markdown редактор!

## Начните писать ваш документ...

- Списки
- **Жирный текст**
- *Курсив*
- [Ссылки](https://example.com)

\`\`\`python
# Код на Python
print("Hello World!")
\`\`\`
`;
        } else {
            return `\\section{Добро пожаловать в LaTeX редактор!}

\\subsection{Начните писать ваш документ...}

Формулы в строке: $E = mc^2$, $a^2 + b^2 = c^2$

Формула в отдельной строке:
$$
\\int_0^1 x^2 dx = \\frac{1}{3}
$$

\\begin{itemize}
    \\item Элемент списка
    \\item Другой элемент
\\end{itemize}

\\textbf{Жирный текст}, \\textit{курсивный текст}
`;
        }
    }

    saveToServer() {
        const content = this.cmEditor.getValue();

        fetch('/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: content,
                mode: this.currentMode
            })
        })
        .then(response => response.json())
        .then(data => {
            this.showSaveStatus('Сохранено');
        })
        .catch(error => {
            console.error('Save error:', error);
            this.showSaveStatus('Ошибка сохранения');
        });
    }

    showSaveStatus(message) {
        const statusElement = document.getElementById('saveStatus');
        statusElement.textContent = message;
        statusElement.style.color = message === 'Сохранено' ? '#27ae60' : '#e74c3c';

        setTimeout(() => {
            statusElement.textContent = 'Сохранено';
            statusElement.style.color = '';
        }, 2000);
    }

    exportHTML() {
    const content = this.cmEditor.getValue();

    // Показываем уведомление о начале экспорта
    this.showSaveStatus('Создание HTML...');

    fetch('/export/html', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content: content,
            mode: this.currentMode
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('HTML export failed');
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `document_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        this.showSaveStatus('HTML создан');
    })
    .catch(error => {
        console.error('HTML export error:', error);
        this.showSaveStatus('Ошибка HTML');
        alert('Ошибка при создании HTML файла');
    });
}

    exportPDF() {
    const content = this.cmEditor.getValue();

    // Показываем уведомление о начале экспорта
    this.showSaveStatus('Создание PDF...');

    fetch('/export/pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content: content,
            mode: this.currentMode
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('PDF export failed');
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `document_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        this.showSaveStatus('PDF создан');
    })
    .catch(error => {
        console.error('PDF export error:', error);
        this.showSaveStatus('Ошибка PDF');
        alert('Ошибка при создании PDF. Убедитесь, что wkhtmltopdf установлен.');
    });
}

    openAIModal() {
        this.aiModal.style.display = 'block';
        this.aiQuestion.focus();
    }

    closeAIModal() {
        this.aiModal.style.display = 'none';
        this.aiMessages.innerHTML = '';
        this.aiQuestion.value = '';
    }

    sendAIQuestion() {
    const question = this.aiQuestion.value.trim();
    if (!question) return;

    this.addAIMessage(question, 'user');
    this.aiQuestion.value = '';

    // Добавляем историю разговора
    const conversationHistory = this.getConversationHistory();

    fetch('/ai-help', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            question: question,
            mode: this.currentMode,
            history: conversationHistory
        })
    })
    .then(response => response.json())
    .then(data => {
        this.addAIMessage(data.response, 'assistant');
        // Сохраняем историю
        this.saveConversationHistory(data.history || []);
    })
    .catch(error => {
        console.error('AI error:', error);
        this.addAIMessage('Ошибка соединения. Попробуйте еще раз.', 'assistant');
    });
}

getConversationHistory() {
    return JSON.parse(localStorage.getItem('ai-conversation') || '[]');
}

saveConversationHistory(history) {
    localStorage.setItem('ai-conversation', JSON.stringify(history.slice(-10))); // Сохраняем последние 10 сообщений
}

    addAIMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ai-${sender}`;
        messageDiv.style.cssText = `
            padding: 0.8rem;
            margin: 0.5rem 0;
            border-radius: 8px;
            border-left: 4px solid ${sender === 'user' ? '#3498db' : '#27ae60'};
            background: ${sender === 'user' ? '#e3f2fd' : '#f5f5f5'};
            white-space: pre-wrap;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9rem;
        `;
        messageDiv.textContent = message;
        this.aiMessages.appendChild(messageDiv);
        this.aiMessages.scrollTop = this.aiMessages.scrollHeight;
    }

    // Метод для получения текущего содержимого редактора
    getContent() {
        return this.cmEditor ? this.cmEditor.getValue() : '';
    }

    // Метод для установки содержимого редактора
    setContent(content) {
        if (this.cmEditor) {
            this.cmEditor.setValue(content);
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.editor = new MarkdownLatexEditor();
});

// Сохранение в localStorage при закрытии страницы
window.addEventListener('beforeunload', () => {
    if (window.editor) {
        window.editor.saveToLocalStorage();
    }
});