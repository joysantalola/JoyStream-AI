

/* JoyStream AI - Assistant v2 */

(function () {

  'use strict';



  const AI_AVATAR = '/joy-ai-avatar.png';



  function aiFormatText(value) {
    const escaped = String(value ?? '').replace(
      /[&<>"']/g,
      ch => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      })[ch]
    );

    return escaped
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  function aiUserAvatar() {

    try {

      const profile = catalog().profile || {};

      const src = profile.profile_image_url;



      if (src && /^https:\/\//i.test(src)) {

        return `<img src="${esc(src)}"

          alt="Joysantalola"

          referrerpolicy="no-referrer">`;

      }

    } catch (_) {}



    return '<span class="joy-ai-avatar-fallback">JS</span>';

  }



  function aiMessage(message) {

    const isUser = message.role === 'user';



    const avatar = isUser

      ? aiUserAvatar()

      : `<img src="${AI_AVATAR}" alt="JoyStream AI">`;



    const content = message.pending

      ? `<div class="joy-ai-thinking">

           <i></i><i></i><i></i>

           <span>Analizando tus estadísticas...</span>

         </div>`

      : `<div class="joy-ai-message-text">

           ${aiFormatText(message.content)}

         </div>`;



    return `

      <article class="joy-ai-message ${isUser ? 'is-user' : 'is-assistant'}">



        <div class="joy-ai-message-avatar">

          ${avatar}

        </div>



        <div class="joy-ai-message-body">



          <div class="joy-ai-message-role">

            ${isUser ? 'TÚ · JOYSANTALOLA' : 'JOY AI · ANALISTA'}

          </div>



          <div class="joy-ai-message-card">

            ${content}



            ${message.meta

              ? `<div class="joy-ai-message-meta">${esc(message.meta)}</div>`

              : ''}

          </div>



        </div>

      </article>

    `;

  }



  // Diagnóstico visible desde la consola para verificar qué versión se ha cargado.
  document.documentElement.dataset.joyAiVersion = '25fix3';

  // NUEVA PÁGINA DEL ASISTENTE

  window.joyAIPage = function () {



    const clips = array('clips').length;

    const videos = array('videos').length;

    const sessions = array('sessions').length;

    const community = array('community').length;



    const messages = state.messages || [];



    const intro = messages.length

      ? messages.map(aiMessage).join('')

      : `

        <div class="joy-ai-welcome">



          <div class="joy-ai-welcome-avatar">

            <img src="${AI_AVATAR}" alt="JoyStream AI">

          </div>



          <div class="joy-ai-welcome-copy">



            <span class="joy-ai-kicker">

              TU ANALISTA PERSONAL

            </span>



            <h3>¡Buenas, Joy!</h3>



            <p>

              Soy JoyStream AI. Estoy aquí para ayudarte

              a entender tus estadísticas de Twitch.

            </p>



            <p>

              Puedo analizar clips, VOD, directos,

              seguidores y suscriptores.

            </p>



            <p class="joy-ai-welcome-note">

              Utilizo tus datos reales de PostgreSQL.

              No invento estadísticas.

            </p>



          </div>

        </div>

      `;



    return head(

      'Asistente de inteligencia artificial',

      'Tu analista personal de Twitch, ejecutado localmente.',

      'JOY INTELLIGENCE'

    ) +



    `

      <section class="joy-ai-workspace">



        <header class="joy-ai-hero">



          <div class="joy-ai-hero-avatar">

            <img src="${AI_AVATAR}" alt="JoyStream AI">

          </div>



          <div class="joy-ai-hero-copy">



            <div class="joy-ai-kicker">

              JOY INTELLIGENCE · PRIVATE AI

            </div>



            <h2>

              JoyStream AI <span>Assistant</span>

            </h2>



            <p>

              Analítica de Twitch con datos reales de PostgreSQL.

            </p>



            <div class="joy-ai-status">

              <span></span>

              Modelo local · Qwen 2.5 3B · Ollama

            </div>



          </div>



          <button

            type="button"

            class="joy-ai-clear"

            id="joy-ai-clear"

            ${messages.length ? '' : 'disabled'}>

            Limpiar conversación

          </button>



        </header>



        <div class="joy-ai-context-strip">



          <div>

            <strong>${fmt(clips)}</strong>

            <span>Clips</span>

          </div>



          <div>

            <strong>${fmt(videos)}</strong>

            <span>VOD</span>

          </div>



          <div>

            <strong>${fmt(sessions)}</strong>

            <span>Directos</span>

          </div>



          <div>

            <strong>${fmt(community)}</strong>

            <span>Muestras comunidad</span>

          </div>



        </div>



        <div class="joy-ai-chat-panel">



          <div

            class="joy-ai-thread"

            id="chat-thread"

            aria-live="polite">



            ${intro}



          </div>



          <div class="joy-ai-suggestions">



            <span>PRUEBA A PREGUNTAR</span>



            <button type="button"

              data-question="Analiza mis clips y dime cuáles destacan por visualizaciones.">

              🏆 Mis mejores clips

            </button>



            <button type="button"

              data-question="Analiza mi último directo: media, pico, evolución y limitaciones.">

              🔴 Mi último directo

            </button>



            <button type="button"

              data-question="¿Qué muestran mis datos de seguidores y suscriptores?">

              📈 Mi comunidad

            </button>



            <button type="button"

              data-question="Propón tres experimentos medibles para mejorar el crecimiento de mi canal.">

              💡 Ideas de crecimiento

            </button>



          </div>



          <form class="joy-ai-composer" id="chat-form">



            <label class="sr-only" for="joy-ai-question">

              Pregunta sobre tus estadísticas

            </label>



            <textarea

              id="joy-ai-question"

              name="question"

              rows="2"

              maxlength="500"

              minlength="5"

              placeholder="Pregunta sobre tus clips, directos, VOD o comunidad..."

              required

              ${state.aiLoading ? 'disabled' : ''}></textarea>



            <div class="joy-ai-composer-footer">



              <span>

                ENTER para enviar · SHIFT + ENTER para nueva línea

              </span>



              <button

                class="btn btn-primary joy-ai-send"

                id="chat-send"

                type="submit"

                ${state.aiLoading ? 'disabled' : ''}>



                ${state.aiLoading ? 'Analizando...' : 'Enviar pregunta ↗'}



              </button>



            </div>



          </form>



          <p class="joy-ai-disclaimer">

            IA local y gratuita. Comprueba las cifras importantes

            frente al dashboard.

          </p>



        </div>



      </section>

    `;

  };





  // NUEVO SISTEMA DE ENVÍO

  window.joyAISendChat = async function (event) {



    event.preventDefault();



    const form = event.currentTarget;

    const input = form.elements.question;



    const question = String(input.value || '').trim();



    if (question.length < 5 || state.aiLoading) {

      return;

    }



    // Recuperar conversación anterior.

    const previousHistory = (state.messages || [])

      .filter(item =>

        !item.pending &&

        (item.role === 'user' || item.role === 'assistant')

      )

      .slice(-8)

      .map(item => ({

        role: item.role,

        content: String(item.content || '').slice(0, 1200)

      }));



    // Añadir pregunta y estado de carga.

    state.messages.push({

      role: 'user',

      content: question

    });



    state.messages.push({

      role: 'assistant',

      content: '',

      pending: true

    });



    state.aiLoading = true;



    render();



    try {



      const result = await api('/ai/analyze', {

        method: 'POST',



        data: {

          question: question,

          history: previousHistory

        },



        timeout: 250000

      });



      // Eliminar indicador de carga.

      state.messages.pop();



      const summary = result.context_summary || {};



      const meta = result.model

        ? `Modelo: ${result.model}

           · Clips: ${result.clips_analyzed ?? 0}

           · VOD: ${result.videos_analyzed ?? 0}

           · Directos: ${result.sessions_analyzed ?? 0}

           · Muestras comunidad: ${summary.community_measurements ?? 0}`

        : '';



      state.messages.push({

        role: 'assistant',

        content: result.answer || 'No se recibió respuesta del modelo.',

        meta: meta

      });



    } catch (error) {



      state.messages.pop();



      state.messages.push({

        role: 'assistant',

        content:

          'No he podido completar el análisis. ' +

          (error.message || 'Comprueba Ollama y FastAPI.')

      });



    } finally {



      state.aiLoading = false;



      render();



      const thread = document.getElementById('chat-thread');



      if (thread) {

        thread.scrollTop = thread.scrollHeight;

      }



      const nextInput = document.getElementById('joy-ai-question');



      if (nextInput) {

        nextInput.focus();

      }

    }

  };





  // LIMPIAR CONVERSACIÓN

  document.addEventListener('click', event => {



    const button = event.target.closest('#joy-ai-clear');



    if (!button || button.disabled) {

      return;

    }



    state.messages = [];



    state.aiLoading = false;



    render();

  });





  // ENTER ENVÍA / SHIFT + ENTER SALTO DE LÍNEA

  document.addEventListener('keydown', event => {



    if (

      event.target &&

      event.target.id === 'joy-ai-question' &&

      event.key === 'Enter' &&

      !event.shiftKey

    ) {



      event.preventDefault();



      const form = document.getElementById('chat-form');



      if (form && !state.aiLoading) {

        form.requestSubmit();

      }

    }

  });



})();
