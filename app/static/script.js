// app/static/script.js
        const translations = {
            fr: {
                title: "Chatbot ISET",
                historyLabel: "Historique",
                clearHistoryLabel: "Effacer",
                pdfLabel: "Téléverser un PDF",
                imageLabel: "Téléverser une image",
                outputLangLabel: "Langue de la réponse",
                voiceLabel: "Utiliser la voix",
                exportLabel: "Exporter en PDF",
                responsePrompt: "Aidez-nous à améliorer ! Fournissez une réponse correcte :",
                placeholder: "Posez votre question...",
                newResponse: "Entrez la réponse correcte...",
                newLink: "Lien (optionnel)...",
                submit: "Soumettre",
                noMatch: "Désolé, je n'ai pas compris."
            },
            en: {
                title: "ISET Chatbot",
                historyLabel: "History",
                clearHistoryLabel: "Clear",
                pdfLabel: "Upload a PDF",
                imageLabel: "Upload an image",
                outputLangLabel: "Response language",
                voiceLabel: "Use voice",
                exportLabel: "Export to PDF",
                responsePrompt: "Help us improve! Provide a correct answer:",
                placeholder: "Ask your question...",
                newResponse: "Enter the correct answer...",
                newLink: "Link (optional)...",
                submit: "Submit",
                noMatch: "Sorry, I didn't understand."
            },
            ar: {
                title: "روبوت الدردشة ISET",
                historyLabel: "السجل",
                clearHistoryLabel: "مسح",
                pdfLabel: "تحميل ملف PDF",
                imageLabel: "تحميل صورة",
                outputLangLabel: "لغة الرد",
                voiceLabel: "استخدام الصوت",
                exportLabel: "تصدير إلى PDF",
                responsePrompt: "ساعدنا على التحسين! قدم إجابة صحيحة:",
                placeholder: "اطرح سؤالك...",
                newResponse: "أدخل الإجابة الصحيحة...",
                newLink: "رابط (اختياري)...",
                submit: "إرسال",
                noMatch: "عذرًا، لم أفهم."
            }
        };

        const errorMessages = {
            'Aucune question ou fichier fourni': {
                fr: 'Veuillez entrer une question ou téléverser un fichier.',
                en: 'Please enter a question or upload a file.',
                ar: 'يرجى إدخال سؤال أو رفع ملف.'
            },
            'Fichier PDF invalide': {
                fr: 'Le fichier doit être un PDF valide.',
                en: 'The file must be a valid PDF.',
                ar: 'يجب أن يكون الملف بصيغة PDF صالحة.'
            },
            'Fichier image invalide (PNG/JPEG requis)': {
                fr: 'Seuls les fichiers PNG ou JPEG sont acceptés.',
                en: 'Only PNG or JPEG files are accepted.',
                ar: 'يتم قبول ملفات PNG أو JPEG فقط.'
            },
            'Fichier PDF trop volumineux (max 5 Mo)': {
                fr: 'Le PDF dépasse la limite de 5 Mo.',
                en: 'The PDF exceeds the 5 MB limit.',
                ar: 'يتجاوز ملف PDF حد 5 ميغابايت.'
            },
            'Fichier image trop volumineux (max 5 Mo)': {
                fr: 'L’image dépasse la limite de 5 Mo.',
                en: 'The image exceeds the 5 MB limit.',
                ar: 'تتجاوز الصورة حد 5 ميغابايت.'
            },
            'Aucune donnée disponible pour répondre.': {
                fr: 'Désolé, je n\'ai pas compris.',
                en: 'Sorry, I didn\'t understand.',
                ar: 'عذرًا، لم أفهم.'
            }
        };

        const chatbox = document.getElementById('chatbox');
        const historyBox = document.getElementById('historyBox');
        const chatForm = document.getElementById('chatForm');
        const userInput = document.getElementById('userInput');
        const sendButton = document.getElementById('sendButton');
        const recordButton = document.getElementById('recordButton');
        const historyButton = document.getElementById('historyButton');
        const exportButton = document.getElementById('exportButton');
        const responseForm = document.getElementById('responseForm');
        const newResponse = document.getElementById('newResponse');
        const newLink = document.getElementById('newLink');
        const newCategory = document.getElementById('newCategory');
        const submitResponse = document.getElementById('submitResponse');
        const uiLang = document.getElementById('ui_lang');
        let recognition;

        let conversations = JSON.parse(localStorage.getItem('conversations')) || [];

        function escapeHTML(str) {
            return str.replace(/[&<>"']/g, match => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            }[match]));
        }

        function isValidURL(str) {
            try {
                new URL(str);
                return true;
            } catch {
                return false;
            }
        }

        function debounce(fn, ms) {
            let timeout;
            return (...args) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => fn(...args), ms);
            };
        }

        function addMessage(content, isUser, data = {}) {
            const div = document.createElement('div');
            div.className = isUser ? 'chat-bubble-user' : 'chat-bubble-bot';
            div.setAttribute('role', 'region');
            div.setAttribute('aria-live', 'polite');
            if (isUser) {
                div.textContent = escapeHTML(content);
            } else {
                const contentDiv = document.createElement('div');
                // Check if confidence is low or answer indicates no match
                const isNoMatch = data.confidence < 0.3 || data.answer === 'Aucune donnée disponible pour répondre.';
                const displayAnswer = isNoMatch ? translations[uiLang.value].noMatch : escapeHTML(data.answer);
                contentDiv.innerHTML = `<strong>Chatbot :</strong> ${displayAnswer}`;
                if (data.extracted_text) {
                    contentDiv.innerHTML += `<br><strong>Contenu extrait :</strong> ${escapeHTML(data.extracted_text)}`;
                }
                if (data.link && isValidURL(data.link) && !isNoMatch) {
                    const link = document.createElement('a');
                    link.href = escapeHTML(data.link);
                    link.className = 'text-blue-500 underline';
                    link.target = '_blank';
                    link.textContent = translations[uiLang.value].link || 'Lien';
                    contentDiv.appendChild(document.createElement('br'));
                    contentDiv.appendChild(link);
                }
                if (data.audio && !isNoMatch) {
                    const audio = document.createElement('audio');
                    audio.controls = true;
                    audio.src = data.audio;
                    audio.onerror = () => addMessage("Erreur : Impossible de lire l'audio.", false);
                    contentDiv.appendChild(document.createElement('br'));
                    contentDiv.appendChild(audio);
                }
                if (!isNoMatch) {
                    const ratingDiv = document.createElement('div');
                    ratingDiv.className = 'mt-2';
                    ratingDiv.innerHTML = `
                        <button class="like-btn text-green-500 hover:text-green-700" data-id="${data.response_id}"><i class="fas fa-thumbs-up"></i></button>
                        <button class="dislike-btn text-red-500 hover:text-red-700" data-id="${data.response_id}"><i class="fas fa-thumbs-down"></i></button>
                    `;
                    contentDiv.appendChild(ratingDiv);
                }
                div.appendChild(contentDiv);
            }
            chatbox.appendChild(div);
            chatbox.scrollTop = chatbox.scrollHeight;
        }

        function updateHistory(page = 1, perPage = 20) {
            const contentDiv = historyBox.querySelector('.history-content') || document.createElement('div');
            contentDiv.className = 'history-content';
            contentDiv.innerHTML = '';
            const start = (page - 1) * perPage;
            const end = start + perPage;
            const paginatedConversations = conversations.slice(start, end);
            paginatedConversations.forEach(conv => {
                const userDiv = document.createElement('div');
                userDiv.className = 'chat-bubble-user';
                userDiv.textContent = escapeHTML(conv.question);
                contentDiv.appendChild(userDiv);

                const botDiv = document.createElement('div');
                botDiv.className = 'chat-bubble-bot';
                botDiv.innerHTML = `
                    <strong>Chatbot :</strong> ${escapeHTML(conv.answer)}
                    ${conv.link && isValidURL(conv.link) ? `<br><a href="${escapeHTML(conv.link)}" class="text-blue-500 underline" target="_blank">${translations[uiLang.value].link || 'Lien'}</a>` : ''}
                    <br><strong>Catégorie :</strong> ${escapeHTML(conv.category)}
                    <br><strong>Évaluation :</strong> ${escapeHTML(conv.rating)}
                `;
                contentDiv.appendChild(botDiv);
            });
            if (!historyBox.querySelector('.history-content')) {
                historyBox.appendChild(contentDiv);
            }
            const pagination = document.createElement('div');
            pagination.className = 'flex justify-center mt-4';
            pagination.innerHTML = `
                <button class="px-4 py-2 bg-indigo-600 text-white rounded-lg disabled:opacity-50" 
                        ${page === 1 ? 'disabled' : ''} 
                        onclick="updateHistory(${page - 1}, ${perPage})">${translations[uiLang.value].previous || 'Précédent'}</button>
                <button class="px-4 py-2 bg-indigo-600 text-white rounded-lg ml-2" 
                        ${end >= conversations.length ? 'disabled' : ''} 
                        onclick="updateHistory(${page + 1}, ${perPage})">${translations[uiLang.value].next || 'Suivant'}</button>
            `;
            contentDiv.appendChild(pagination);
            historyBox.scrollTop = historyBox.scrollHeight;
        }

        function updateInterfaceLang(lang) {
            const t = translations[lang];
            document.body.dir = lang === 'ar' ? 'rtl' : 'ltr';
            document.getElementById('title').textContent = t.title;
            document.getElementById('historyLabel').textContent = t.historyLabel;
            document.getElementById('clearHistoryLabel').textContent = t.clearHistoryLabel;
            document.getElementById('pdfLabel').textContent = t.pdfLabel;
            document.getElementById('imageLabel').textContent = t.imageLabel;
            document.getElementById('outputLangLabel').textContent = t.outputLangLabel;
            document.getElementById('voiceLabel').textContent = t.voiceLabel;
            document.getElementById('exportLabel').textContent = t.exportLabel;
            document.getElementById('responsePrompt').textContent = t.responsePrompt;
            userInput.placeholder = t.placeholder;
            newResponse.placeholder = t.newResponse;
            newLink.placeholder = t.newLink;
            submitResponse.textContent = t.submit;
            updateHistory();
        }

        uiLang.addEventListener('change', () => {
            updateInterfaceLang(uiLang.value);
        });

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(chatForm);
            const message = userInput.value.trim();
            const pdfFile = formData.get('pdf_file');
            const imageFile = formData.get('image_file');

            if (!message && !pdfFile.name && !imageFile.name) {
                addMessage(errorMessages['Aucune question ou fichier fourni'][uiLang.value], false);
                return;
            }

            if (pdfFile.name && (pdfFile.size > 5 * 1024 * 1024 || !pdfFile.name.endsWith('.pdf'))) {
                addMessage(errorMessages['Fichier PDF invalide'][uiLang.value], false);
                return;
            }
            if (imageFile.name && (imageFile.size > 5 * 1024 * 1024 || !['image/png', 'image/jpeg'].includes(imageFile.type))) {
                addMessage(errorMessages['Fichier image invalide (PNG/JPEG requis)'][uiLang.value], false);
                return;
            }

            sendButton.disabled = true;
            sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            if (message) addMessage(message, true);

            try {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/chat', true);
                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable) {
                        const percent = (event.loaded / event.total) * 100;
                        addMessage(`${translations[uiLang.value].uploading || 'Téléversement'} : ${Math.round(percent)}%`, false);
                    }
                };
                xhr.onload = () => {
                    if (xhr.status === 200) {
                        const data = JSON.parse(xhr.responseText);
                        if (data.error) {
                            throw new Error(errorMessages[data.error]?.[uiLang.value] || data.error);
                        }
                        const conversation = {
                            question: message || (translations[uiLang.value].fileUploaded || "Fichier uploadé"),
                            answer: data.confidence < 0.3 ? translations[uiLang.value].noMatch : data.answer,
                            link: data.link,
                            category: data.category,
                            response_id: data.response_id,
                            rating: 'Non évalué'
                        };
                        conversations.push(conversation);
                        if (conversations.length > 100) conversations = conversations.slice(-100);
                        localStorage.setItem('conversations', JSON.stringify(conversations));
                        addMessage(data.answer, false, data);
                        updateHistory();
                        if (data.ask_for_response || data.confidence < 0.3) {
                            responseForm.classList.remove('hidden');
                            responseForm.dataset.question = message || (translations[uiLang.value].fileUploaded || "Fichier uploadé");
                        }
                        if (chatbox.querySelector('.chat-bubble-bot')?.textContent.includes('Chargement')) {
                            chatbox.querySelector('.chat-bubble-bot').remove();
                        }
                    } else {
                        const errorData = JSON.parse(xhr.responseText);
                        throw new Error(errorMessages[errorData.error]?.[uiLang.value] || errorData.error || 'Erreur réseau ou serveur');
                    }
                };
                xhr.onerror = () => {
                    throw new Error(translations[uiLang.value].networkError || 'Erreur réseau');
                };
                xhr.send(formData);
            } catch (error) {
                addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${error.message}`, false);
                console.error('Erreur chat:', error);
            } finally {
                sendButton.disabled = false;
                sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
                userInput.value = '';
            }
        });

        submitResponse.addEventListener('click', async () => {
            const question = responseForm.dataset.question;
            const response = newResponse.value.trim();
            const link = newLink.value.trim();
            const category = newCategory.value;
            if (!response) {
                addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${translations[uiLang.value].noResponse || 'Veuillez entrer une réponse.'}`, false);
                return;
            }

            try {
                const res = await fetch('/add_response', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json', 
                        'X-CSRFToken': document.getElementById('csrf_token').value 
                    },
                    body: JSON.stringify({ question, response, link, category })
                });
                if (!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorMessages[errorData.error]?.[uiLang.value] || errorData.error || 'Erreur lors de l’ajout de la réponse');
                }
                const data = await res.json();
                if (data.error) throw new Error(errorMessages[data.error]?.[uiLang.value] || data.error);

                responseForm.classList.add('hidden');
                newResponse.value = '';
                newLink.value = '';
                newCategory.value = 'Général';
                addMessage(translations[uiLang.value].responseAdded || "Merci ! Votre réponse a été ajoutée.", false);
                conversations.push({ question, answer: response, link, category, rating: 'Non évalué' });
                if (conversations.length > 100) conversations = conversations.slice(-100);
                localStorage.setItem('conversations', JSON.stringify(conversations));
                updateHistory();
            } catch (error) {
                addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${error.message}`, false);
                console.error('Erreur add_response:', error);
            }
        });

        chatbox.addEventListener('click', async (e) => {
            if (e.target.classList.contains('like-btn') || e.target.classList.contains('dislike-btn')) {
                const responseId = e.target.dataset.id;
                const rating = e.target.classList.contains('like-btn') ? 'like' : 'dislike';
                try {
                    const res = await fetch('/rate', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json', 
                            'X-CSRFToken': document.getElementById('csrf_token').value 
                        },
                        body: JSON.stringify({ response_id: responseId, rating })
                    });
                    if (!res.ok) {
                        const errorData = await res.json();
                        throw new Error(errorMessages[errorData.error]?.[uiLang.value] || errorData.error || 'Erreur lors de l’enregistrement de l’évaluation');
                    }
                    const data = await res.json();
                    if (data.error) throw new Error(errorMessages[data.error]?.[uiLang.value] || data.error);

                    const otherBtn = e.target.classList.contains('like-btn')
                        ? e.target.parentElement.querySelector('.dislike-btn')
                        : e.target.parentElement.querySelector('.like-btn');
                    e.target.classList.add('text-yellow-500', 'font-bold');
                    otherBtn.classList.remove('text-yellow-500', 'font-bold');
                    e.target.disabled = true;
                    otherBtn.disabled = true;
                    const index = conversations.findIndex(c => c.response_id === responseId);
                    if (index !== -1) {
                        conversations[index].rating = rating;
                        localStorage.setItem('conversations', JSON.stringify(conversations));
                        updateHistory();
                    }
                } catch (error) {
                    addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${error.message}`, false);
                    console.error('Erreur rate:', error);
                }
            }
        });

        historyButton.addEventListener('click', () => {
            historyBox.classList.toggle('hidden');
            chatbox.classList.toggle('hidden');
            if (!historyBox.classList.contains('hidden')) {
                updateHistory();
            }
        });

        exportButton.addEventListener('click', async () => {
            if (!conversations || conversations.length === 0) {
                addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${translations[uiLang.value].noConversations || 'Aucune conversation à exporter.'}`, false);
                return;
            }

            exportButton.disabled = true;
            exportButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + (translations[uiLang.value].exporting || 'Exportation...');
            try {
                const response = await fetch('/export_conversations', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json', 
                        'X-CSRFToken': document.getElementById('csrf_token').value 
                    },
                    body: JSON.stringify({ conversations })
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorMessages[errorData.error]?.[uiLang.value] || errorData.error || 'Erreur lors de l’exportation du PDF');
                }
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'conversation.pdf';
                a.click();
                window.URL.revokeObjectURL(url);
                addMessage(translations[uiLang.value].exportSuccess || "PDF exporté avec succès.", false);
            } catch (error) {
                addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${error.message}`, false);
                console.error('Erreur export PDF:', error);
            } finally {
                exportButton.disabled = false;
                exportButton.innerHTML = '<i class="fas fa-file-pdf mr-2"></i> <span id="exportLabel">' + (translations[uiLang.value].exportLabel || 'Exporter') + '</span>';
            }
        });

        userInput.addEventListener('keypress', debounce((e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendButton.click();
            }
        }, 200));

        recordButton.addEventListener('click', () => {
            if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
                addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${translations[uiLang.value].speechNotSupported || 'La reconnaissance vocale n\'est pas supportée par ce navigateur.'}`, false);
                return;
            }
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (recordButton.classList.contains('recording')) {
                recognition.stop();
                recordButton.classList.remove('recording', 'bg-red-500');
                return;
            }
            recognition = new SpeechRecognition();
            recognition.lang = uiLang.value === 'ar' ? 'ar-SA' : uiLang.value === 'en' ? 'en-US' : 'fr-FR';
            recognition.onresult = (event) => {
                userInput.value = event.results[0][0].transcript;
                chatForm.dispatchEvent(new Event('submit'));
            };
            recognition.onerror = (event) => {
                addMessage(`${translations[uiLang.value].error || 'Erreur'} : ${translations[uiLang.value].speechError || 'Échec de la reconnaissance vocale.'} (${event.error})`, false);
            };
            recognition.onend = () => {
                recordButton.classList.remove('recording', 'bg-red-500');
            };
            recognition.start();
            recordButton.classList.add('recording', 'bg-red-500');
        });

        document.getElementById('pdf_file').addEventListener('change', (e) => {
            const label = document.getElementById('pdfLabel');
            const clearBtn = document.getElementById('clearPdf');
            if (e.target.files[0]) {
                label.textContent = `${translations[uiLang.value].pdfLabel.split(':')[0]} : ${e.target.files[0].name}`;
                clearBtn.classList.remove('hidden');
            } else {
                label.textContent = translations[uiLang.value].pdfLabel;
                clearBtn.classList.add('hidden');
            }
        });

        document.getElementById('clearPdf').addEventListener('click', () => {
            document.getElementById('pdf_file').value = '';
            document.getElementById('pdfLabel').textContent = translations[uiLang.value].pdfLabel;
            document.getElementById('clearPdf').classList.add('hidden');
        });

        document.getElementById('image_file').addEventListener('change', (e) => {
            const label = document.getElementById('imageLabel');
            const clearBtn = document.getElementById('clearImage');
            if (e.target.files[0]) {
                label.textContent = `${translations[uiLang.value].imageLabel.split(':')[0]} : ${e.target.files[0].name}`;
                clearBtn.classList.remove('hidden');
                const reader = new FileReader();
                reader.onload = (event) => {
                    const img = document.createElement('img');
                    img.src = event.target.result;
                    img.className = 'mt-2 max-w-full rounded-lg';
                    img.style.maxHeight = '100px';
                    chatbox.appendChild(img);
                    chatbox.scrollTop = chatbox.scrollHeight;
                };
                reader.readAsDataURL(e.target.files[0]);
            } else {
                label.textContent = translations[uiLang.value].imageLabel;
                clearBtn.classList.add('hidden');
            }
        });

        document.getElementById('clearImage').addEventListener('click', () => {
            document.getElementById('image_file').value = '';
            document.getElementById('imageLabel').textContent = translations[uiLang.value].imageLabel;
            document.getElementById('clearImage').classList.add('hidden');
        });

        document.getElementById('clearHistoryButton').addEventListener('click', () => {
            conversations = [];
            localStorage.setItem('conversations', JSON.stringify(conversations));
            historyBox.querySelector('.history-content').innerHTML = `<p class="text-gray-500">${translations[uiLang.value].historyCleared || 'Historique vidé.'}</p>`;
        });

        updateInterfaceLang(uiLang.value);
