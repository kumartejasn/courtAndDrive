document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('case-form');
    const submitBtn = document.getElementById('submit-btn');
    const refreshCaptchaBtn = document.getElementById('refresh-captcha');
    const captchaImage = document.getElementById('captcha-image');
    const messageArea = document.getElementById('message-area');
    const resultsArea = document.getElementById('results-area');
    const resultsContent = document.getElementById('results-content');
    
    let currentSessionId = null;

    
    const yearSelect = document.getElementById('case-year');
    const currentYear = new Date().getFullYear();
    for (let year = currentYear; year >= 1980; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
    
    
    const getNewCaptcha = async () => {
        showMessage('Loading new CAPTCHA...', 'info');
        try {
            const response = await fetch('/api/captcha');
            if (!response.ok) throw new Error('Failed to load CAPTCHA from server.');

            const data = await response.json();
            captchaImage.src = `data:image/png;base64,${data.captcha_image}`;
            currentSessionId = data.session_id;
            hideMessage();
        } catch (error) {
            showMessage(error.message, 'error');
        }
    };

    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Fetching...';
        showMessage('Fetching case data, this may take a moment...', 'info');
        resultsArea.classList.add('hidden');

        const formData = new FormData(form);
        const payload = {
            session_id: currentSessionId,
            case_type: formData.get('case-type'),
            case_number: formData.get('case-number'),
            case_year: formData.get('case-year'),
            captcha_text: formData.get('captcha-text'),
        };

        try {
            const response = await fetch('/api/case-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok) {
                
                throw new Error(result.detail || 'An unknown error occurred.');
            }

            displayResults(result);
            hideMessage();
        } catch (error) {
            showMessage(error.message, 'error');
            
            getNewCaptcha();
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Fetch Data';
        }
    });

    refreshCaptchaBtn.addEventListener('click', getNewCaptcha);

  
    function showMessage(msg, type = 'info') {
        messageArea.textContent = msg;
        messageArea.className = `mt-4 text-center p-3 rounded-md ${type === 'error' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`;
        messageArea.classList.remove('hidden');
    }

    function hideMessage() {
        messageArea.classList.add('hidden');
    }

    function displayResults(data) {
        resultsContent.innerHTML = `
            <p><strong>Parties:</strong> ${data.parties}</p>
            <p><strong>Filing Date:</strong> ${data.filing_date}</p>
            <p><strong>Next Hearing Date:</strong> ${data.next_hearing_date}</p>
            <div><strong>Orders/Judgments:</strong>
                <ul class="list-disc list-inside ml-4">
                    ${data.pdf_links.map(link => `<li><a href="${link}" target="_blank" class="text-blue-600 hover:underline">Download PDF</a></li>`).join('')}
                </ul>
            </div>
        `;
        resultsArea.classList.remove('hidden');
    }

    getNewCaptcha();
});