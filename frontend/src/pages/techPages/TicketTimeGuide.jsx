import React from 'react';
import {
  BookOpen,
  Clock,
  ArrowRight,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Timer,
  ShieldCheck,
  Lightbulb,
  ListChecks,
  MousePointerClick
} from 'lucide-react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { SLA_TARGETS } from '../../components/MttrCard';

// Lifecycle stages — same colours as the "Where the resolution time goes" bar on the MTTR report
const STAGE_COLORS = {
  assign: '#38bdf8',   // sky-400
  ack: '#fbbf24',      // amber-400
  travel: '#818cf8',   // indigo-400
  onsite: '#10b981',   // emerald-500
  close: '#d1d5db'     // gray-300
};

// Worked example used by the timeline diagram (minutes after the ticket was created)
const EXAMPLE = [
  { key: 'created', label: 'Ticket created', status: 'New', time: '09:00', minute: 0 },
  { key: 'assigned', label: 'Assigned', status: 'Assigned', time: '09:30', minute: 30 },
  { key: 'ack', label: 'Acknowledged', status: 'In Progress', time: '09:45', minute: 45 },
  { key: 'arrived', label: 'Arrived on site', status: 'On Site', time: '11:00', minute: 120 },
  { key: 'resolved', label: 'Fixed', status: 'Resolved', time: '12:00', minute: 180 },
  { key: 'closed', label: 'Closed', status: 'Closed', time: '12:15', minute: 195 }
];

const STATUS_STEPS = [
  {
    status: 'New',
    who: 'Automatic',
    when: 'The customer submits a request or an email creates the ticket.',
    records: 'CREATED_AT',
    effect: 'The MTTR and SLA clock starts.',
    chip: 'bg-yellow-100 text-yellow-800'
  },
  {
    status: 'Assigned',
    who: 'Automatic / dispatcher',
    when: 'The ticket is assigned to you (auto-assignment or manual).',
    records: 'ASSIGNED_AT',
    effect: 'Ends "waiting for assignment". Only the first assignment counts.',
    chip: 'bg-sky-100 text-sky-800'
  },
  {
    status: 'In Progress',
    who: 'You',
    when: 'As soon as you accept the ticket and start working on it.',
    records: 'ACKNOWLEDGED_AT',
    effect: 'Ends "time to acknowledge". Only the first time counts.',
    chip: 'bg-blue-100 text-blue-800'
  },
  {
    status: 'On Site',
    who: 'You (field visits)',
    when: 'The moment you arrive at the customer premises. Skip it for remote fixes.',
    records: 'ARRIVED_AT',
    effect: 'Ends "travel to site", starts "on-site work".',
    chip: 'bg-indigo-100 text-indigo-800'
  },
  {
    status: 'Resolved',
    who: 'You',
    when: 'Service is restored and you have checked it works. Time Spent is required.',
    records: 'RESOLVED_AT',
    effect: 'The MTTR clock stops here.',
    chip: 'bg-green-100 text-green-800'
  },
  {
    status: 'Closed',
    who: 'You',
    when: 'After the customer confirms or paperwork is finished.',
    records: 'CLOSED_AT',
    effect: 'Does not change MTTR (it already stopped at Resolved).',
    chip: 'bg-gray-100 text-gray-800'
  }
];

/** Timeline diagram: the worked example drawn to scale, with the MTTR bracket underneath. */
const TimelineDiagram = () => {
  const x0 = 70;
  const span = 760; // pixels for 180 minutes (created -> resolved)
  const x = (minute) => x0 + (minute / 180) * span;
  const barY = 118;
  const segments = [
    { from: 0, to: 30, color: STAGE_COLORS.assign, label: 'Waiting for assignment', dur: '30 min' },
    { from: 30, to: 45, color: STAGE_COLORS.ack, label: 'Acknowledge', dur: '15 min' },
    { from: 45, to: 120, color: STAGE_COLORS.travel, label: 'Travel to site', dur: '1 h 15 min' },
    { from: 120, to: 180, color: STAGE_COLORS.onsite, label: 'On-site work', dur: '1 h' },
    { from: 180, to: 195, color: STAGE_COLORS.close, label: '', dur: '' }
  ];

  return (
    <svg viewBox="0 0 960 300" className="w-full h-auto" role="img" aria-labelledby="timeline-title timeline-desc">
      <title id="timeline-title">Ticket timeline example</title>
      <desc id="timeline-desc">
        Created 09:00, assigned 09:30, acknowledged 09:45, arrived on site 11:00, resolved 12:00, closed 12:15.
        MTTR is created to resolved, 3 hours.
      </desc>

      {/* Stage bars */}
      {segments.map((s) => (
        <rect key={s.from} x={x(s.from)} y={barY} width={x(s.to) - x(s.from)} height={22} fill={s.color} rx={3} />
      ))}

      {/* Durations inside bars and stage names above */}
      {segments.filter((s) => s.label).map((s) => {
        const mid = (x(s.from) + x(s.to)) / 2;
        const narrow = x(s.to) - x(s.from) < 90;
        return (
          <g key={`l-${s.from}`}>
            <text x={mid} y={barY + 15} textAnchor="middle" fontSize="12" fontWeight="700" fill="#111827">
              {narrow ? s.dur.replace(' min', 'm') : s.dur}
            </text>
            {!narrow && (
              <text x={mid} y={barY - 10} textAnchor="middle" fontSize="12" fill="#4b5563">{s.label}</text>
            )}
          </g>
        );
      })}
      {/* Label for the narrow "acknowledge" segment, offset so it does not collide */}
      <text x={(x(30) + x(45)) / 2} y={barY - 10} textAnchor="middle" fontSize="12" fill="#4b5563">Ack</text>

      {/* Event markers */}
      {EXAMPLE.map((e, i) => {
        const cx = x(e.minute);
        const labelY = i % 2 === 0 ? 40 : 66; // alternate rows so neighbouring labels never overlap
        return (
          <g key={e.key}>
            <line x1={cx} y1={labelY + 6} x2={cx} y2={barY + 30} stroke="#9ca3af" strokeDasharray="3 3" />
            <circle cx={cx} cy={barY + 11} r={7} fill="#ffffff" stroke="#111827" strokeWidth="2" />
            <text x={cx} y={labelY - 12} textAnchor="middle" fontSize="12" fontWeight="700" fill="#111827">{e.label}</text>
            <text x={cx} y={labelY + 2} textAnchor="middle" fontSize="11" fill="#2563eb">status: {e.status}</text>
            <text x={cx} y={barY + 50} textAnchor="middle" fontSize="12" fontWeight="600" fill="#374151">{e.time}</text>
          </g>
        );
      })}

      {/* MTTR bracket: created -> resolved */}
      <path
        d={`M ${x(0)} 190 V 202 H ${x(180)} V 190`}
        fill="none"
        stroke="#7c3aed"
        strokeWidth="2.5"
      />
      <text x={(x(0) + x(180)) / 2} y={226} textAnchor="middle" fontSize="15" fontWeight="800" fill="#6d28d9">
        MTTR for this ticket = 12:00 − 09:00 = 3 hours
      </text>
      <text x={(x(0) + x(180)) / 2} y={246} textAnchor="middle" fontSize="12" fill="#4b5563">
        = 30 min waiting + 15 min acknowledge + 1 h 15 min travel + 1 h on-site work
      </text>

      {/* Closing note */}
      <text x={x(195)} y={226} textAnchor="middle" fontSize="11" fill="#6b7280">not part</text>
      <text x={x(195)} y={240} textAnchor="middle" fontSize="11" fill="#6b7280">of MTTR</text>

      {/* SLA note */}
      <text x={x(0)} y={284} fontSize="12" fill="#047857">
        High priority SLA target is 8 h → 3 h is within SLA ✓
      </text>
    </svg>
  );
};

/** Status flow: the order technicians move a ticket through, with the reopen path. */
const StatusFlow = () => (
  <div className="flex flex-wrap items-center gap-2">
    {STATUS_STEPS.map((s, i) => (
      <React.Fragment key={s.status}>
        <span className={`px-3 py-1.5 rounded-full text-sm font-semibold ${s.chip}`}>{s.status}</span>
        {i < STATUS_STEPS.length - 1 && <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" aria-hidden="true" />}
      </React.Fragment>
    ))}
    <span className="flex items-center gap-1.5 text-xs text-gray-600 ml-1 mt-1 sm:mt-0">
      <RotateCcw className="w-3.5 h-3.5 text-red-500" aria-hidden="true" />
      Reopen (Open / In Progress after Resolved) clears the resolved time and Time Spent
    </span>
  </div>
);

/** A drawing of the update form on the ticket page, with numbered callouts. */
const UpdateFormMock = () => {
  const Badge = ({ n }) => (
    <span className="absolute left-0 top-0 w-6 h-6 rounded-full bg-[#00ABE4] text-white text-xs font-bold flex items-center justify-center shadow">
      {n}
    </span>
  );
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="relative bg-gray-50 border border-gray-200 rounded-xl p-5 space-y-4" aria-hidden="true">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Ticket page → right column</p>
        <div className="relative pl-9">
          <Badge n={1} />
          <label className="block text-sm font-medium text-gray-700 mb-1">Update Status</label>
          <div className="w-full border border-gray-300 rounded-lg p-2 bg-white text-sm flex justify-between">
            <span>On Site (arrived at customer)</span>
            <span className="text-gray-400">▾</span>
          </div>
        </div>
        <div className="relative pl-9">
          <Badge n={2} />
          <label className="block text-sm font-medium text-gray-700 mb-1">Time Spent</label>
          <div className="w-full border border-gray-300 rounded-lg p-2 bg-white text-sm text-gray-500">60 mins</div>
        </div>
        <div className="relative pl-9">
          <Badge n={3} />
          <label className="block text-sm font-medium text-gray-700 mb-1">Add Work Note</label>
          <div className="w-full border border-gray-300 rounded-lg p-2 bg-white text-sm text-gray-500 h-16">
            Replaced damaged drop cable, optical power now -19 dBm.
          </div>
        </div>
        <div className="relative pl-9">
          <Badge n={4} />
          <div className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg text-sm text-center">Save Update</div>
        </div>
      </div>

      <ol className="space-y-4 text-sm text-gray-700">
        <li className="flex gap-3">
          <span className="w-6 h-6 rounded-full bg-[#00ABE4] text-white text-xs font-bold flex items-center justify-center flex-shrink-0">1</span>
          <span>
            <strong>Update Status</strong>: pick the status for what is happening <em>right now</em>.
            The time is recorded when you press Save; it cannot be back-dated.
          </span>
        </li>
        <li className="flex gap-3">
          <span className="w-6 h-6 rounded-full bg-[#00ABE4] text-white text-xs font-bold flex items-center justify-center flex-shrink-0">2</span>
          <span>
            <strong>Time Spent</strong>: your hands-on work, e.g. <code>45 mins</code> or <code>1.5 hours</code>.
            Required before <strong>Resolved</strong> or <strong>Closed</strong>. It is your effort, not MTTR.
          </span>
        </li>
        <li className="flex gap-3">
          <span className="w-6 h-6 rounded-full bg-[#00ABE4] text-white text-xs font-bold flex items-center justify-center flex-shrink-0">3</span>
          <span><strong>Work Note</strong>: what you found and did. Optional, but helps the next technician and the AI suggestions.</span>
        </li>
        <li className="flex gap-3">
          <span className="w-6 h-6 rounded-full bg-[#00ABE4] text-white text-xs font-bold flex items-center justify-center flex-shrink-0">4</span>
          <span><strong>Save Update</strong>: saves the status and stamps the time in the database.</span>
        </li>
        <li className="flex gap-3 text-gray-500">
          <MousePointerClick className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
          <span>Open it from <strong>My Tickets</strong> → <strong>View</strong>. Only the assigned technician can update a ticket.</span>
        </li>
      </ol>
    </div>
  );
};

const Section = ({ icon, title, children }) => (
  <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6">
    <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
      {React.createElement(icon, { className: 'w-5 h-5 text-[#00ABE4]', 'aria-hidden': true })}
      {title}
    </h2>
    {children}
  </section>
);

const TicketTimeGuide = () => (
  <div className="flex min-h-screen bg-gray-50">
    <Sidebar />
    <div className="flex-1 flex flex-col min-h-screen">
      <Header />
      <main className="p-6 md:p-8 flex-1">
        <div className="max-w-6xl mx-auto space-y-6">

          {/* Page header */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 flex items-start gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#00ABE4] to-blue-600 text-white flex items-center justify-center shadow-md flex-shrink-0">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">How Ticket Time Works</h1>
              <p className="text-gray-600 text-sm mt-1 max-w-3xl">
                Every status you set records a time. Those times build your MTTR and SLA numbers.
                Set each status at the moment it happens and your report will be accurate.
              </p>
            </div>
          </div>

          {/* The one formula */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 rounded-xl p-5 bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-100">
              <p className="text-xs font-semibold uppercase tracking-wider text-purple-700 flex items-center gap-1.5">
                <Timer className="w-3.5 h-3.5" aria-hidden="true" /> MTTR (Mean Time To Resolve)
              </p>
              <p className="text-2xl font-extrabold text-purple-900 mt-2">Resolved time − Created time</p>
              <p className="text-sm text-purple-800 mt-1">
                averaged over all your resolved tickets. It is the full time the customer waited:
                assignment, acknowledgement, travel and repair.
              </p>
            </div>
            <div className="rounded-xl p-5 bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100">
              <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" aria-hidden="true" /> Avg Work Time
              </p>
              <p className="text-lg font-bold text-amber-900 mt-2">The Time Spent you type</p>
              <p className="text-sm text-amber-800 mt-1">Your hands-on effort. Shown separately; it is not MTTR.</p>
            </div>
          </div>

          <Section icon={Timer} title="Example: one truck-roll ticket from start to finish">
            <div className="overflow-x-auto">
              <div className="min-w-[640px]">
                <TimelineDiagram />
              </div>
            </div>
            <div className="flex flex-wrap gap-x-5 gap-y-2 mt-4 text-xs text-gray-600">
              {[
                ['Waiting for assignment', STAGE_COLORS.assign, 'Created → Assigned'],
                ['Time to acknowledge', STAGE_COLORS.ack, 'Assigned → In Progress'],
                ['Travel to site', STAGE_COLORS.travel, 'In Progress → On Site'],
                ['On-site work', STAGE_COLORS.onsite, 'On Site → Resolved']
              ].map(([label, color, range]) => (
                <span key={label} className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm" style={{ background: color }} />
                  <strong className="text-gray-800">{label}</strong> ({range})
                </span>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-3">
              These four parts are shown as the "Where the resolution time goes" bar on your MTTR Report.
            </p>
          </Section>

          <Section icon={ListChecks} title="What each status means and what it records">
            <StatusFlow />
            <div className="overflow-x-auto mt-5">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-gray-500 border-b border-gray-200">
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Who sets it</th>
                    <th className="py-2 pr-3">When to set it</th>
                    <th className="py-2 pr-3">Time recorded</th>
                    <th className="py-2">Effect on MTTR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {STATUS_STEPS.map((s) => (
                    <tr key={s.status} className="align-top">
                      <td className="py-3 pr-3">
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${s.chip}`}>{s.status}</span>
                      </td>
                      <td className="py-3 pr-3 text-gray-700 whitespace-nowrap">{s.who}</td>
                      <td className="py-3 pr-3 text-gray-700">{s.when}</td>
                      <td className="py-3 pr-3"><code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{s.records}</code></td>
                      <td className="py-3 text-gray-700">{s.effect}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section icon={MousePointerClick} title="How to update a ticket">
            <UpdateFormMock />
          </Section>

          <Section icon={ShieldCheck} title="SLA targets (created → resolved)">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                ['Critical', 'border-red-200 text-red-700', 'Area outage, OLT/PON down, business fully down'],
                ['High', 'border-orange-200 text-orange-700', 'One customer with no service at all'],
                ['Medium', 'border-yellow-200 text-yellow-700', 'Slow or intermittent service'],
                ['Low', 'border-blue-200 text-blue-700', 'Questions, moves, configuration']
              ].map(([p, cls, desc]) => (
                <div key={p} className={`rounded-xl border p-4 ${cls}`}>
                  <p className="text-xs font-bold uppercase">{p}</p>
                  <p className="text-2xl font-extrabold text-gray-900 mt-1">{SLA_TARGETS[p.toLowerCase()]} h</p>
                  <p className="text-xs text-gray-600 mt-1">{desc}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-3">
              The SLA clock runs on real time from when the ticket is created, including nights and weekends.
              On open tickets you see "On Track", "SLA remaining" (70% of the target used) or "Overdue".
            </p>
          </Section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Section icon={CheckCircle2} title="Do">
              <ul className="space-y-2.5 text-sm text-gray-700">
                {[
                  'Set In Progress as soon as you accept a ticket.',
                  'Set On Site the moment you arrive, before you start work.',
                  'Set Resolved right after you confirm service is back, not at the end of the day.',
                  'Enter Time Spent as your real hands-on time.',
                  'Write a short work note: what was wrong and what you changed.'
                ].map((t) => (
                  <li key={t} className="flex gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" aria-hidden="true" />{t}
                  </li>
                ))}
              </ul>
            </Section>
            <Section icon={XCircle} title="Avoid">
              <ul className="space-y-2.5 text-sm text-gray-700">
                {[
                  'Updating several statuses at once later: all of them get the same time and the breakdown is lost.',
                  'Resolving before the fix is verified; reopening clears the resolved time and Time Spent.',
                  'Entering more Time Spent than the ticket was open: it is ignored as invalid.',
                  'Using On Site for remote fixes: skip it, go straight from In Progress to Resolved.'
                ].map((t) => (
                  <li key={t} className="flex gap-2">
                    <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" aria-hidden="true" />{t}
                  </li>
                ))}
              </ul>
            </Section>
          </div>

          <Section icon={Lightbulb} title="Common questions">
            <dl className="space-y-4 text-sm">
              {[
                ['Does closing a ticket change my MTTR?', 'No. MTTR stops at the first Resolved. Closed only records when the ticket was closed.'],
                ['I set In Progress twice. Which time counts?', 'The first one. Assigned, In Progress and On Site keep their first time, so going back and forth does not move them.'],
                ['What happens if I reopen a ticket?', 'The resolved time, closed time and Time Spent are cleared. MTTR uses the final resolution, so the ticket counts again when you resolve it.'],
                ['Which timezone are the times in?', 'Times are stored in UTC and shown in your own local time, so they are correct wherever you are.'],
                ['Why is my MTTR different from my Time Spent?', 'MTTR includes waiting, acknowledgement and travel. Time Spent is only your hands-on work.']
              ].map(([q, a]) => (
                <div key={q}>
                  <dt className="font-semibold text-gray-900">{q}</dt>
                  <dd className="text-gray-600 mt-0.5">{a}</dd>
                </div>
              ))}
            </dl>
          </Section>
        </div>
      </main>
    </div>
  </div>
);

export default TicketTimeGuide;
