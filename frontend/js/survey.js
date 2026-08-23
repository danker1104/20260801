/**
 * 음식 취향 설문 UI와 로컬 추천 결과.
 */

let surveyStep = 0;
let surveyAnswers = [];
let surveyResult = null;

function renderSurveyStep() {
    const content = document.getElementById('surveyContent');
    const progress = document.getElementById('surveyProgress');
    const backButton = document.getElementById('surveyBackBtn');
    const nextButton = document.getElementById('surveyNextBtn');
    const question = SURVEY_QUESTIONS[surveyStep];

    progress.textContent = `${surveyStep + 1}/${SURVEY_QUESTIONS.length}`;
    backButton.disabled = surveyStep === 0;
    nextButton.textContent = surveyStep === SURVEY_QUESTIONS.length - 1 ? '결과 보기' : '다음';
    content.innerHTML = `
        <p class="survey-question">${question.question}</p>
        <div class="survey-options" role="radiogroup" aria-label="${question.question}">
            ${question.options.map((option, index) => `
                <button class="survey-option${surveyAnswers[surveyStep] === index ? ' selected' : ''}"
                        type="button" role="radio" aria-checked="${surveyAnswers[surveyStep] === index}"
                        data-option-index="${index}">
                    <span class="survey-option-emoji" aria-hidden="true">${option.emoji}</span>
                    <span class="survey-option-label">${option.label}</span>
                </button>
            `).join('')}
        </div>
    `;

    content.querySelectorAll('.survey-option').forEach((option) => {
        option.addEventListener('click', () => {
            surveyAnswers[surveyStep] = Number(option.dataset.optionIndex);
            renderSurveyStep();
        });
    });
}

function calculateSurveyResult() {
    const scores = Object.fromEntries(SURVEY_CATEGORIES.map((category) => [category, 0]));
    surveyAnswers.forEach((answerIndex, questionIndex) => {
        const option = SURVEY_QUESTIONS[questionIndex].options[answerIndex];
        SURVEY_CATEGORIES.forEach((category) => {
            scores[category] += option.scores[category];
        });
    });

    const highestScore = Math.max(...Object.values(scores));
    const categories = SURVEY_CATEGORIES.filter((category) => scores[category] === highestScore);
    return { scores, categories: categories.slice(0, 2) };
}

function buildSurveyReason(result) {
    const answerLabels = surveyAnswers.map((answer, index) => SURVEY_QUESTIONS[index].options[answer].label);
    const categoryText = result.categories.join('과 ');
    return `${answerLabels[1]} 취향과 ${answerLabels[4]} 선택을 중심으로 ${categoryText}을(를) 추천해요. ${answerLabels[3]}도 반영한 오늘의 맞춤 결과입니다.`;
}

function renderSurveyResult() {
    const content = document.getElementById('surveyContent');
    const progress = document.getElementById('surveyProgress');
    const backButton = document.getElementById('surveyBackBtn');
    const nextButton = document.getElementById('surveyNextBtn');
    const result = calculateSurveyResult();
    surveyResult = result;

    progress.textContent = '완료';
    backButton.disabled = false;
    nextButton.textContent = '추천 식당 보기';
    content.innerHTML = `
        <div class="survey-result">
            <p class="survey-result-label">오늘의 추천</p>
            <h3>${result.categories.join(' · ')}</h3>
            <p class="survey-reason">${buildSurveyReason(result)}</p>
            <div class="survey-score-list" aria-label="카테고리별 점수">
                ${SURVEY_CATEGORIES.map((category) => `
                    <div class="survey-score-row">
                        <span>${category}</span>
                        <strong>${result.scores[category]}점</strong>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function closeSurvey() {
    const modal = document.getElementById('surveyModal');
    modal.style.display = 'none';
    document.body.classList.remove('survey-open');
}

function handleSurveyNext() {
    if (surveyResult) {
        if (typeof window.applySurveyRecommendations === 'function') {
            window.applySurveyRecommendations(surveyResult.categories);
        }
        closeSurvey();
        return;
    }

    if (surveyAnswers[surveyStep] === undefined) {
        showError('답변을 선택해주세요');
        return;
    }

    if (surveyStep === SURVEY_QUESTIONS.length - 1) {
        renderSurveyResult();
    } else {
        surveyStep += 1;
        renderSurveyStep();
    }
}

function handleSurveyBack() {
    if (surveyResult) {
        surveyResult = null;
        surveyStep = SURVEY_QUESTIONS.length - 1;
        renderSurveyStep();
        return;
    }
    if (surveyStep > 0) {
        surveyStep -= 1;
        renderSurveyStep();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('surveyModal');
    document.getElementById('surveyNextBtn').addEventListener('click', handleSurveyNext);
    document.getElementById('surveyBackBtn').addEventListener('click', handleSurveyBack);

    renderSurveyStep();
    modal.style.display = 'flex';
    document.body.classList.add('survey-open');
});
