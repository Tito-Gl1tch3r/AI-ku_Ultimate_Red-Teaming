import React, { useRef, useState, useEffect } from 'react' 
import FullCalendar from '@fullcalendar/react' 
import dayGridPlugin from '@fullcalendar/daygrid' 
import timeGridPlugin from '@fullcalendar/timegrid' 
import interactionPlugin from '@fullcalendar/interaction' 
import listPlugin from '@fullcalendar/list' 
import { ChevronLeft, ChevronRight } from 'lucide-react' 
import { OverlayTrigger, Tooltip } from 'react-bootstrap'

export default function CalendarSection({ events, initialView = 'dayGridMonth' }) { 
  const [view, setView] = useState(initialView) 
  const calRef = useRef(null) 
  const [calTitle, setCalTitle] = useState('') 

  // Only shows tooltip if text is truncated
  const TruncatedEvent = ({ title, time }) => {
    const [show, setShow] = useState(false)
    const titleRef = useRef(null)

    const handleMouseEnter = () => {
      const el = titleRef.current
      // Check if the text is wider than its container
      if (el && el.scrollWidth > el.clientWidth) {
        setShow(true)
      }
    }

    const handleMouseLeave = () => {
      setShow(false)
    }

    return (
      <OverlayTrigger
        show={show}
        placement="top"
        overlay={<Tooltip id={`tooltip-${title}`}>{title}</Tooltip>}
      >
        <div 
          className="mlf-timechip-inner"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <span className="mlf-timechip-dot"></span>
          <span className="mlf-timechip-time">{time}</span>
          <span ref={titleRef} className="mlf-timechip-title">
            {title}
          </span>
        </div>
      </OverlayTrigger>
    )
  }
 
  // Prevent popover from closing when scrolling main page
  useEffect(() => {
    const handleMousedown = (e) => {
      const target = e.target;
      
      if (target.closest('.fc-popover')) return;

      const rect = target.getBoundingClientRect();
      const isVerticalScrollbar = e.clientX >= rect.left + target.clientWidth && e.clientX <= rect.right;
      const isHorizontalScrollbar = e.clientY >= rect.top + target.clientHeight && e.clientY <= rect.bottom;

      if (isVerticalScrollbar || isHorizontalScrollbar) {
        e.stopPropagation();
      }
    };

    const handleScroll = (e) => {
      const target = e.target;
      const isInternalCalendarScroll = target.classList?.contains('fc-scroller');

      if (isInternalCalendarScroll) {
        const popover = document.querySelector('.fc-popover');
        if (popover) {
          const closeBtn = popover.querySelector('.fc-popover-close');
          closeBtn?.click();
        }
      }
    };

    document.addEventListener('mousedown', handleMousedown, true);
    document.addEventListener('scroll', handleScroll, true);

    return () => {
      document.removeEventListener('mousedown', handleMousedown, true);
      document.removeEventListener('scroll', handleScroll, true);
    };
  }, []);
  
  const goto = (dir) => { 
    const api = calRef.current?.getApi() 
    if (!api) return 
    dir === 'prev' ? api.prev() : api.next() 
  } 

  const goToToday = () => {
    const api = calRef.current?.getApi()
    if (!api) return
    api.today()
  }
 
  const switchView = (v) => { 
    const api = calRef.current?.getApi() 
    setView(v) 
    api?.changeView(v) 
  } 
 
  return ( 
    <div className="calblock rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-3"> 
      <div className="flex items-center justify-between px-1 pb-2"> 
        <div className="flex items-center gap-2">
          <div className="calendar-nav inline-flex rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10"> 
            <button onClick={() => goto('prev')} className="px-3 py-2"> 
              <ChevronLeft size={16} /> 
            </button> 
            <button onClick={() => goto('next')} className="px-3 py-2"> 
              <ChevronRight size={16} /> 
            </button> 
          </div>
          <button 
            onClick={goToToday}
            className="px-3 py-2 text-sm font-medium rounded-xl ring-1 ring-black/10 dark:ring-white/10 hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          >
            Today
          </button>
        </div>
 
        <div className="text-sm md:text-base font-semibold text-slate-900 dark:text-white"> 
          {calTitle} 
        </div> 
 
        <div className="inline-flex rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 calendar-view-switch"> 
          {[ 
            { id: 'dayGridMonth', label: 'Month' }, 
            { id: 'timeGridWeek', label: 'Week' }, 
            { id: 'timeGridDay', label: 'Day' }, 
            { id: 'listWeek', label: 'List' }, 
          ].map(({ id, label }, i, arr) => { 
            const active = view === id 
            const edge = 
              i === 0 ? 'rounded-l-xl' : 
              i === arr.length - 1 ? 'rounded-r-xl' : 'rounded-none' 
            return ( 
              <button 
                key={id} 
                onClick={() => switchView(id)} 
                className={`px-3 py-2 text-sm focus:outline-none focus:ring-0 ${edge} ${ 
                  active 
                    ? 'bg-primary/20 text-[var(--mlf-primary)]' 
                    : 'hover:bg-black/5 dark:hover:bg-white/10' 
                }`} 
              > 
                {label} 
              </button> 
            ) 
          })} 
        </div> 
      </div> 
 
      <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 calendar-wrapper"> 
        <FullCalendar 
          ref={calRef} 
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]} 
          initialView={view} 
          headerToolbar={false} 
          events={events} 
          height={view === 'listWeek' ? 'auto' : 560} 
          contentHeight={view === 'listWeek' ? 'auto' : undefined} 
          expandRows={true} 
          firstDay={1}
          dayMaxEvents={3} 
          slotEventOverlap={false} 
          eventMaxStack={2}
          slotMinTime="06:00:00" 
          slotMaxTime="22:00:00" 
          slotDuration="00:30:00" 
          slotLabelFormat={{ hour: 'numeric', minute: '2-digit', meridiem: 'short' }} 
          nowIndicator={true} 
          displayEventEnd={true} 
          eventOrder="-allDay,start,-duration" 
          moreLinkClick="popover" 
          moreLinkContent={(arg) => `+${arg.num} more`} 
          eventTimeFormat={{ hour: 'numeric', minute: '2-digit', meridiem: 'short' }} 
          datesSet={(arg) => setCalTitle(arg.view.title)} 
          eventClassNames={(arg) => { 
            const t = arg.view.type || '' 
            if (t === 'dayGridMonth') { 
              const ev = arg.event 
              const start = ev.start 
              const end = ev.end 
              const endMinus1 = end ? new Date(end.getTime() - 1) : null 
              const isMulti = 
                ev.allDay || 
                (endMinus1 && 
                  (start.getFullYear() !== endMinus1.getFullYear() || 
                    start.getMonth() !== endMinus1.getMonth() || 
                    start.getDate() !== endMinus1.getDate())) 
              return [isMulti ? 'mlf-banner-event' : 'mlf-dot-event'] 
            } 
            if (t === 'timeGridWeek' || t === 'timeGridDay') { 
              return ['mlf-timechip'] 
            } 
            return t.startsWith('list') ? ['rounded-md'] : [] 
          }} 
          eventContent={(arg) => { 
            const t = arg.view.type 
            const title = arg.event.title || 'Untitled'
            const time = (arg.timeText || '').toLowerCase()

            // Month view
            if (t === 'dayGridMonth') { 
              const ev = arg.event 
              const start = ev.start 
              const end = ev.end 
              const endMinus1 = end ? new Date(end.getTime() - 1) : null 
              const isMulti = 
                ev.allDay || 
                (endMinus1 && 
                  (start.getFullYear() !== endMinus1.getFullYear() || 
                    start.getMonth() !== endMinus1.getMonth() || 
                    start.getDate() !== endMinus1.getDate())) 
              
              if (isMulti) {
                return <div className="mlf-banner">{title}</div> 
              }
              
              return (
                <div className="mlf-dot-row"> 
                  <span className="mlf-dot"></span> 
                  <span className="mlf-dot-time">{time}</span> 
                  <span className="mlf-dot-title">{title}</span> 
                </div>
              )
            } 

            // Week7day view
            if (t === 'timeGridWeek' || t === 'timeGridDay') { 
              return <TruncatedEvent title={title} time={time} />
            } 

            // List view
            return (
              <div className="px-2 py-1 text-xs">
                <div className="font-medium truncate">{title}</div>
                <div className="opacity-90">{time}</div>
              </div>
            )
          }}
        /> 
      </div> 
    </div> 
  ) 
}