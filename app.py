from flask import Flask, render_template, request, jsonify, send_file
import markdown as md
import pdfkit
import os
import tempfile
from datetime import datetime
import requests

wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe' # указать свой путь к установленной библиотеке
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Конфигурация PDF экспорта
PDF_CONFIG = {
    'page-size': 'A4',
    'margin-top': '0.75in',
    'margin-right': '0.75in',
    'margin-bottom': '0.75in',
    'margin-left': '0.75in',
    'encoding': "UTF-8",
    'no-outline': None,
    'enable-local-file-access': None
}


class DocumentManager:
    def __init__(self):
        self.markdown_content = ""
        self.latex_content = ""
        self.current_mode = "markdown"

    def save_content(self, content, mode):
        if mode == "markdown":
            self.markdown_content = content
        else:
            self.latex_content = content
        self.current_mode = mode
        return True

    def get_content(self, mode):
        if mode == "markdown":
            return self.markdown_content
        else:
            return self.latex_content

    def markdown_to_html(self, content):
        return md.markdown(content, extensions=['extra', 'codehilite', 'tables'])

    def latex_to_html(self, content):
        lines = content.split('\n')
        processed_lines = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith('\\section{') and stripped.endswith('}'):
                title = stripped[9:-1]
                processed_lines.append(f'<h2>{title}</h2>')
            elif stripped.startswith('\\subsection{') and stripped.endswith('}'):
                title = stripped[12:-1]
                processed_lines.append(f'<h3>{title}</h3>')
            elif stripped.startswith('\\subsubsection{') and stripped.endswith('}'):
                title = stripped[15:-1]
                processed_lines.append(f'<h4>{title}</h4>')
            elif stripped == '\\begin{itemize}':
                processed_lines.append('<ul>')
            elif stripped == '\\end{itemize}':
                processed_lines.append('</ul>')
            elif stripped == '\\begin{enumerate}':
                processed_lines.append('<ol>')
            elif stripped == '\\end{enumerate}':
                processed_lines.append('</ol>')
            elif stripped.startswith('\\item'):
                item_content = stripped[5:].strip()
                processed_lines.append(f'<li>{item_content}</li>')
            elif stripped == '\\begin{theorem}':
                processed_lines.append('<div class="theorem"><strong>Теорема.</strong>')
            elif stripped == '\\end{theorem}':
                processed_lines.append('</div>')
            elif stripped == '\\begin{proof}':
                processed_lines.append('<div class="proof"><strong>Доказательство.</strong>')
            elif stripped == '\\end{proof}':
                processed_lines.append('</div>')
            elif stripped == '\\begin{verbatim}':
                processed_lines.append('<pre class="verbatim">')
            elif stripped == '\\end{verbatim}':
                processed_lines.append('</pre>')
            else:
                formatted_line = self.process_text_formatting(line)
                processed_lines.append(formatted_line)

        result = '\n'.join(processed_lines)
        return f'<div class="latex-content">{result}</div>'

    def process_text_formatting(self, text):
        formatted = text

        while '\\texttt{' in formatted and '}' in formatted:
            start = formatted.find('\\texttt{')
            end = self.find_matching_brace(formatted, start + 7)
            if end > start:
                content = formatted[start + 8:end]
                formatted = formatted[:start] + f'<code>{content}</code>' + formatted[end + 1:]

        while '\\textit{' in formatted and '}' in formatted:
            start = formatted.find('\\textit{')
            end = self.find_matching_brace(formatted, start + 7)
            if end > start:
                content = formatted[start + 8:end]
                formatted = formatted[:start] + f'<em>{content}</em>' + formatted[end + 1:]

        while '\\textbf{' in formatted and '}' in formatted:
            start = formatted.find('\\textbf{')
            end = self.find_matching_brace(formatted, start + 7)
            if end > start:
                content = formatted[start + 8:end]
                formatted = formatted[:start] + f'<strong>{content}</strong>' + formatted[end + 1:]

        return formatted

    def find_matching_brace(self, text, start_pos):
        if start_pos < 0 or start_pos >= len(text) or text[start_pos] != '{':
            return -1

        count = 1
        pos = start_pos + 1

        while pos < len(text) and count > 0:
            if text[pos] == '{':
                count += 1
            elif text[pos] == '}':
                count -= 1
            pos += 1

        return pos - 1 if count == 0 else -1

    def export_to_pdf(self, content, mode):
        try:
            if mode == "markdown":
                html_content = self.markdown_to_html(content)
            else:
                html_content = self.latex_to_html(content)

            # Создаем полный HTML документ
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
                    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
                    h2 {{ color: #2c3e50; }}
                    h3 {{ color: #34495e; }}
                    code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
                    pre {{ background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                    .theorem {{ background: #e8f5e8; border-left: 4px solid #27ae60; padding: 10px; margin: 10px 0; }}
                    .proof {{ background: #e3f2fd; border-left: 4px solid #3498db; padding: 10px; margin: 10px 0; }}
                    ul, ol {{ margin: 10px 0; padding-left: 20px; }}
                    li {{ margin: 5px 0; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Настройка пути к wkhtmltopdf
            if os.name == 'nt':  # Windows
                wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            else:  # Linux/Mac
                config = pdfkit.configuration()

            # Создание PDF
            pdf = pdfkit.from_string(full_html, False, configuration=config, options=PDF_CONFIG)

            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf)
                return tmp.name

        except Exception as e:
            print(f"PDF export error: {e}")
            return None

    def export_to_html(self, content, mode):
        if mode == "markdown":
            html_content = self.markdown_to_html(content)
        else:
            html_content = self.latex_to_html(content)

        # Создаем полный HTML документ
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Экспортированный документ</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
                h2 {{ color: #2c3e50; }}
                h3 {{ color: #34495e; }}
                code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
                pre {{ background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                .theorem {{ background: #e8f5e8; border-left: 4px solid #27ae60; padding: 10px; margin: 10px 0; }}
                .proof {{ background: #e3f2fd; border-left: 4px solid #3498db; padding: 10px; margin: 10px 0; }}
                ul, ol {{ margin: 10px 0; padding-left: 20px; }}
                li {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        return full_html


doc_manager = DocumentManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/save', methods=['POST'])
def save_content():
    content = request.json.get('content', '')
    mode = request.json.get('mode', 'markdown')

    success = doc_manager.save_content(content, mode)

    return jsonify({
        'status': 'success' if success else 'error',
        'timestamp': datetime.now().isoformat(),
        'mode': mode
    })


@app.route('/load', methods=['POST'])
def load_content():
    mode = request.json.get('mode', 'markdown')
    content = doc_manager.get_content(mode)

    return jsonify({
        'content': content,
        'mode': mode
    })

@app.route('/preview', methods=['POST'])
def preview():
    content = request.json.get('content', '')
    mode = request.json.get('mode', 'markdown')

    if mode == "markdown":
        html_content = doc_manager.markdown_to_html(content)
    else:
        html_content = doc_manager.latex_to_html(content)

    return jsonify({'html': html_content})


@app.route('/export/pdf', methods=['POST'])
def export_pdf():
    content = request.json.get('content', '')
    mode = request.json.get('mode', 'markdown')

    pdf_path = doc_manager.export_to_pdf(content, mode)

    if pdf_path:
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'document_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
    else:
        return jsonify({'error': 'PDF export failed'}), 500


@app.route('/export/html', methods=['POST'])
def export_html():
    content = request.json.get('content', '')
    mode = request.json.get('mode', 'markdown')

    html_content = doc_manager.export_to_html(content, mode)

    # Создаем временный файл
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    return send_file(
        tmp_path,
        as_attachment=True,
        download_name=f'document_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html',
        mimetype='text/html'
    )


def get_smart_fallback_response(question, mode):
    question_lower = question.lower()

    # Базовые приветствия
    greetings = ['привет', 'здравствуй', 'добрый', 'hello', 'hi', 'хей']
    if any(greet in question_lower for greet in greetings):
        responses = [
            f"Привет! Я ваш помощник по {mode}. Чем могу помочь?",
            f"Здравствуйте! Готов помочь с {mode} разметкой.",
            f"Приветствую! Задавайте вопросы по {mode}."
        ]
        import random
        return random.choice(responses)

    # Благодарности
    thanks = ['спасибо', 'благодар', 'thanks', 'thank you']
    if any(thank in question_lower for thank in thanks):
        return "Пожалуйста! Если есть еще вопросы - обращайтесь! 😊"

    # Контекстно-зависимые ответы
    context_responses = {
        'markdown': {
            'заголовок': 'В Markdown заголовки:\n```markdown\n# H1\n## H2\n### H3\n#### H4\n```',
            'жирный': '**жирный текст** или __жирный текст__',
            'курсив': '*курсив* или _курсив_',
            'список': 'Маркированный:\n- пункт 1\n- пункт 2\n\nНумерованный:\n1. первый\n2. второй',
            'ссылка': '[текст](https://example.com)',
            'код': 'Встроенный: `код`\nБлок:\n```python\nprint("hello")\n```',
            'таблиц': '| Столбец 1 | Столбец 2 |\n|-----------|-----------|\n| данные    | данные    |',
            'формул': 'Формулы через MathJax:\nВ строке: $E=mc^2$\nОтдельно: $$\n\\sum_{i=1}^n i\n$$',
            'изображен': '![Alt текст](image.jpg "подсказка")'
        },
        'latex': {
            'заголовок': '\\section{Раздел}\n\\subsection{Подраздел}\n\\subsubsection{Подподраздел}',
            'жирный': '\\textbf{жирный текст}',
            'курсив': '\\textit{курсивный текст}',
            'список': '\\begin{itemize}\n\\item пункт\n\\end{itemize}\n\\begin{enumerate}\n\\item первый\n\\end{enumerate}',
            'ссылка': '\\href{https://example.com}{текст ссылки}',
            'код': '\\begin{verbatim}\nкод\n\\end{verbatim}',
            'таблиц': '\\begin{tabular}{|c|c|}\n\\hline\nячейка & ячейка \\\\\n\\hline\n\\end{tabular}',
            'формул': 'В строке: $E=mc^2$\nОтдельно: \\[\n\\int_a^b f(x)dx\n\\]',
            'изображен': '\\includegraphics[width=0.5\\textwidth]{image.png}'
        }
    }

    # Ищем ключевые слова
    for keyword, response in context_responses[mode].items():
        if keyword in question_lower:
            return f"В {mode}:\n{response}"

    # Умный ответ на основе часто задаваемых вопросов
    faq_patterns = {
        'разница между': f"{mode} имеет свой синтаксис. Что именно сравниваете?",
        'лучший способ': "Зависит от контекста. Опишите вашу задачу подробнее.",
        'ошибк': "Покажите ваш код, и я помогу найти ошибку.",
        'не работает': "Давайте разберемся вместе. Покажите ваш код.",
        'начать': f"Отличное начало! Рекомендую начать с основ {mode}.",
        'основы': f"Основы {mode}: заголовки, текст, списки, ссылки. Что интересует?"
    }

    for pattern, response in faq_patterns.items():
        if pattern in question_lower:
            return response

    # Персонализированный ответ
    import random
    responses = [
        f"В {mode} я могу помочь с синтаксисом, примерами кода и лучшими практиками.",
        f"Расскажите, что вы хотите создать в {mode}, и я подскажу как это сделать.",
        f"Задайте конкретный вопрос о {mode} - например, про заголовки, списки или формулы.",
        f"Чем могу помочь с {mode}? Могу показать примеры кода и объяснить синтаксис."
    ]

    return random.choice(responses)


@app.route('/ai-help', methods=['POST'])
def ai_help():
    try:
        question = request.json.get('question', '')
        mode = request.json.get('mode', 'markdown')

        # Бесплатный AI API (пример)
        response = requests.post(
            'https://api.deepinfra.com/v1/openai/chat/completions',
            json={
                "model": "mistralai/Mistral-7B-Instruct-v0.1",
                "messages": [
                    {
                        "role": "system",
                        "content": f"Ты помощник для редактора {mode}. Отвечай кратко и помогай с синтаксисом."
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "max_tokens": 200
            },
            headers={"Authorization": "Bearer YOUR_API_KEY"}  # Нужно получить ключ
        )

        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            return jsonify({'response': ai_response})
        else:
            # Fallback если API не доступно
            return jsonify({'response': get_smart_fallback_response(question, mode)})

    except Exception as e:
        print(f"AI error: {e}")
        return jsonify({'response': get_smart_fallback_response(question, mode)})


if __name__ == '__main__':
    app.run(debug=True)