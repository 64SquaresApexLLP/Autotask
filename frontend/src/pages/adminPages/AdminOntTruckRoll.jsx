import React, { useState, useEffect, useCallback } from 'react';
import {
  Truck, Users, MapPin, Wrench, Cloud, AlertTriangle, Sparkles, Search,
  Download, RefreshCw, Loader2, AlertCircle, ChevronRight, X, TrendingUp,
  Award, CheckCircle2, Info, LayoutGrid, Table2, PieChart as PieChartIcon,
  Calendar, Layers, ShieldAlert, ChevronLeft, RotateCcw
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { ontTruckRollService } from '../../services/ontTruckRollService';

const SOLUTION_COLORS = { 'Replaced Ont': '#00ABE4', 'Replaced Wall Wart': '#8b5cf6', 'Replaced Controller': '#f59e0b' };
const WEATHER_MATCH_COLORS = {
  MATCHED: '#10b981',
  AREA_CENTROID_APPROXIMATE: '#f59e0b',
  CITY_CENTROID_APPROXIMATE: '#f97316',
  GEOCODE_FAILED: '#ef4444',
  NO_WEATHER_DATA: '#94a3b8',
};

const TABS = [
  { key: 'overview', label: 'Executive Overview', icon: LayoutGrid },
  { key: 'details', label: 'Truck Roll Details', icon: Table2 },
  { key: 'trends', label: 'Time Trends', icon: TrendingUp },
  { key: 'location', label: 'Location / Service Area', icon: MapPin },
  { key: 'repeat', label: 'Repeat Addresses', icon: RotateCcw },
  { key: 'technician', label: 'Technician Analysis', icon: Wrench },
  { key: 'weather', label: 'Weather Analysis', icon: Cloud },
  { key: 'cortex', label: 'AI Summaries', icon: Sparkles },
];

const fmtNum = (n) => (n === null || n === undefined ? '—' : Number(n).toLocaleString());
const fmtPct = (n) => (n === null || n === undefined ? '—' : `${Number(n).toFixed(1)}%`);
const fmtDate = (d) => (d ? new Date(d).toLocaleString() : '—');

const WeatherMatchBadge = ({ status }) => {
  const labels = {
    MATCHED: 'Exact', AREA_CENTROID_APPROXIMATE: 'Approx. (Area)', CITY_CENTROID_APPROXIMATE: 'Approx. (City)',
    GEOCODE_FAILED: 'No Location', NO_WEATHER_DATA: 'No Weather',
  };
  const color = WEATHER_MATCH_COLORS[status] || '#94a3b8';
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border"
      style={{ color, borderColor: color + '55', backgroundColor: color + '15' }}>
      {labels[status] || status || '—'}
    </span>
  );
};

const KpiCard = ({ label, value, icon: Icon, color = 'blue', hint }) => {
  const colorMap = {
    blue: 'bg-blue-50 text-[#00ABE4]', purple: 'bg-purple-50 text-purple-600', emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600', red: 'bg-red-50 text-red-600', indigo: 'bg-indigo-50 text-indigo-600',
  };
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center justify-between">
      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider truncate">{label}</p>
        <h3 className="text-xl font-bold text-gray-900 mt-1">{value}</h3>
        {hint && <p className="text-[11px] text-gray-400 mt-0.5">{hint}</p>}
      </div>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ml-2 ${colorMap[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
    </div>
  );
};

const SectionCard = ({ title, subtitle, icon: Icon, children, right }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6">
    <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-5 h-5 text-[#00ABE4]" />}
        <div>
          <h3 className="text-base font-bold text-gray-900">{title}</h3>
          {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
    {children}
  </div>
);

const EmptyState = ({ message = 'No records match the current filters.' }) => (
  <div className="text-center py-10 text-sm text-gray-400">{message}</div>
);

const LoadingBlock = () => (
  <div className="flex items-center justify-center py-16">
    <Loader2 className="w-7 h-7 animate-spin text-[#00ABE4]" />
  </div>
);

const ErrorBlock = ({ message }) => (
  <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg flex items-center space-x-2 text-sm">
    <AlertCircle className="w-5 h-5 flex-shrink-0" />
    <span>{message}</span>
  </div>
);

const DETAIL_FIELDS = [
  ['ONT_TRUCK_ROLL_ID', 'ID'], ['ORDER_NUMBER', 'Order Number'], ['ACCOUNT', 'Account'], ['ACCOUNT_NUMBER', 'Account Number'],
  ['ENTERED_DATE', 'Entered Date'], ['SOLUTION_DATE', 'Solution Date'], ['SOLUTION_ENTRY_USER', 'Technician'],
  ['PROBLEM', 'Problem'], ['SOLUTION', 'Solution'], ['ORDER_STATUS', 'Order Status'],
  ['SERVICE_ADDRESS', 'Service Address'], ['SERVICE_CITY', 'Service City'], ['SERVICE_REVENUE_AREA', 'Service Revenue Area'],
  ['RESOLUTION_HOURS', 'Resolution (hrs)'], ['RESOLUTION_MINUTES', 'Resolution (min)'],
  ['ENTERED_YEAR', 'Entered Year'], ['ENTERED_MONTH', 'Entered Month'],
  ['IS_DUPLICATE_ORDER_NUMBER', 'Duplicate Order #?'], ['IS_DATE_ANOMALY', 'Date Anomaly?'],
  ['LATITUDE', 'Latitude'], ['LONGITUDE', 'Longitude'], ['LOCATION_MATCH_TYPE', 'Location Match Type'],
  ['ORIGINAL_GEOCODING_STATUS', 'Original Geocoding Status'],
  ['INCIDENT_TIMESTAMP_UTC', 'Incident Timestamp (UTC)'], ['WEATHER_HOUR_UTC', 'Matched Weather Hour (UTC)'],
  ['WEATHER_TIMESTAMP_UTC', 'Weather Observation Timestamp (UTC)'], ['WEATHER_MATCH_STATUS', 'Weather Match Status'],
  ['TEMPERATURE_C', 'Temperature (°C)'], ['PRECIPITATION_MM', 'Precipitation (mm)'], ['RAIN_MM', 'Rain (mm)'],
  ['SNOWFALL_CM', 'Snowfall (cm)'], ['WIND_SPEED_KMH', 'Wind Speed (km/h)'], ['WIND_GUST_KMH', 'Wind Gusts (km/h)'],
  ['RELATIVE_HUMIDITY_PCT', 'Relative Humidity (%)'], ['WEATHER_CODE', 'Weather Code'], ['WEATHER_CONDITION', 'Weather Condition'],
  ['IS_SEVERE_WEATHER', 'Severe Weather?'],
];

const RecordDetailModal = ({ record, onClose }) => {
  if (!record) return null;
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b border-gray-200 px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-gray-900">Truck Roll #{record.ONT_TRUCK_ROLL_ID}</h3>
            <p className="text-xs text-gray-500">Order {record.ORDER_NUMBER} · {record.SERVICE_ADDRESS}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-4 h-4 text-gray-500" /></button>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
          {DETAIL_FIELDS.map(([key, label]) => {
            let val = record[key];
            if (typeof val === 'boolean') val = val ? 'Yes' : 'No';
            if (key.includes('DATE') || key.includes('TIMESTAMP')) val = fmtDate(val);
            return (
              <div key={key} className="flex justify-between text-xs border-b border-gray-50 pb-1.5">
                <span className="text-gray-500">{label}</span>
                <span className="text-gray-900 font-medium text-right ml-2">{val === null || val === undefined || val === '' ? '—' : String(val)}</span>
              </div>
            );
          })}
        </div>
        {(record.LOCATION_MATCH_TYPE && record.LOCATION_MATCH_TYPE !== 'EXACT') && (
          <div className="mx-5 mb-5 bg-amber-50 border border-amber-200 text-amber-700 text-xs px-3 py-2 rounded-lg flex items-start gap-2">
            <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>Weather shown is approximate — from the {record.LOCATION_MATCH_TYPE === 'CITY_CENTROID' ? 'city' : 'service-area'} average location, not this record's exact address.</span>
          </div>
        )}
      </div>
    </div>
  );
};

const AdminOntTruckRoll = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});
  const [data, setData] = useState({});
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [exportingCSV, setExportingCSV] = useState(false);
  const [exportError, setExportError] = useState('');

  // Truck Roll Details tab state
  const [filters, setFilters] = useState({
    search: '', date_from: '', date_to: '', solution: '', service_city: '',
    service_revenue_area: '', technician: '', order_status: '', weather_match_status: '', location_match_type: '',
  });
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const setLoad = (key, val) => setLoading((p) => ({ ...p, [key]: val }));
  const setErr = (key, val) => setErrors((p) => ({ ...p, [key]: val }));
  const setD = (key, val) => setData((p) => ({ ...p, [key]: val }));

  const loadOverview = useCallback(async () => {
    setLoad('overview', true); setErr('overview', '');
    try {
      const [kpi, cortex] = await Promise.all([
        ontTruckRollService.getKpiSummary(),
        ontTruckRollService.getCortexSummaries().catch(() => ({ rows: [] })),
      ]);
      setD('kpi', kpi);
      setD('cortex', cortex.rows || []);
    } catch (e) {
      setErr('overview', e.message || 'Failed to load overview.');
    } finally { setLoad('overview', false); }
  }, []);

  const loadRecords = useCallback(async (f = filters, p = page) => {
    setLoad('details', true); setErr('details', '');
    try {
      const cleanFilters = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
      const res = await ontTruckRollService.getRecords({ ...cleanFilters, limit: pageSize, offset: p * pageSize });
      setD('records', res);
    } catch (e) {
      setErr('details', e.message || 'Failed to load truck roll records.');
    } finally { setLoad('details', false); }
  }, [filters, page]);



  const loadTrends = useCallback(async () => {
    setLoad('trends', true); setErr('trends', '');
    try { setD('trends', (await ontTruckRollService.getMonthlyTrend()).rows || []); }
    catch (e) { setErr('trends', e.message || 'Failed to load monthly trend.'); }
    finally { setLoad('trends', false); }
  }, []);

  const loadLocation = useCallback(async () => {
    setLoad('location', true); setErr('location', '');
    try { setD('location', (await ontTruckRollService.getServiceAreas()).rows || []); }
    catch (e) { setErr('location', e.message || 'Failed to load service areas.'); }
    finally { setLoad('location', false); }
  }, []);

  const loadRepeat = useCallback(async () => {
    setLoad('repeat', true); setErr('repeat', '');
    try { setD('repeat', (await ontTruckRollService.getAddresses(1, 2038)).rows || []); }
    catch (e) { setErr('repeat', e.message || 'Failed to load addresses.'); }
    finally { setLoad('repeat', false); }
  }, []);

  const loadTechnician = useCallback(async () => {
    setLoad('technician', true); setErr('technician', '');
    try { setD('technician', (await ontTruckRollService.getTechnicians()).rows || []); }
    catch (e) { setErr('technician', e.message || 'Failed to load technicians.'); }
    finally { setLoad('technician', false); }
  }, []);

  const loadWeather = useCallback(async () => {
    setLoad('weather', true); setErr('weather', '');
    try { setD('weather', await ontTruckRollService.getWeatherStats()); }
    catch (e) { setErr('weather', e.message || 'Failed to load weather stats.'); }
    finally { setLoad('weather', false); }
  }, []);



  const loadCortex = useCallback(async () => {
    setLoad('cortex', true); setErr('cortex', '');
    try { setD('cortexFull', (await ontTruckRollService.getCortexSummaries()).rows || []); }
    catch (e) { setErr('cortex', e.message || 'Failed to load Cortex summaries.'); }
    finally { setLoad('cortex', false); }
  }, []);

  // Lazy-load each tab's data the first time it's opened (performance: don't
  // load all 3,040 records or every aggregate up front).
  useEffect(() => {
    if (activeTab === 'overview' && !data.kpi) loadOverview();
    if (activeTab === 'details' && !data.records) loadRecords();
    if (activeTab === 'trends' && !data.trends) loadTrends();
    if (activeTab === 'location' && !data.location) loadLocation();
    if (activeTab === 'repeat' && !data.repeat) loadRepeat();
    if (activeTab === 'technician' && !data.technician) loadTechnician();
    if (activeTab === 'weather' && !data.weather) loadWeather();
    if (activeTab === 'cortex' && !data.cortexFull) loadCortex();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  useEffect(() => { if (activeTab === 'details') loadRecords(filters, page); }, [page]); // eslint-disable-line

  const applyFilters = () => { setPage(0); loadRecords(filters, 0); };
  const resetFilters = () => {
    const cleared = { search: '', date_from: '', date_to: '', solution: '', service_city: '', service_revenue_area: '', technician: '', order_status: '', weather_match_status: '', location_match_type: '' };
    setFilters(cleared); setPage(0); loadRecords(cleared, 0);
  };
  const filtersActive = Object.values(filters).some((v) => v);

  const drillToAddress = (address) => {
    const cleared = { search: address, date_from: '', date_to: '', solution: '', service_city: '', service_revenue_area: '', technician: '', order_status: '', weather_match_status: '', location_match_type: '' };
    setFilters(cleared); setPage(0); setActiveTab('details'); loadRecords(cleared, 0);
  };
  const drillToSolution = (solution) => {
    const next = { ...filters, solution }; setFilters(next); setPage(0); setActiveTab('details'); loadRecords(next, 0);
  };
  const drillToTechnician = (tech) => {
    const next = { ...filters, technician: tech }; setFilters(next); setPage(0); setActiveTab('details'); loadRecords(next, 0);
  };
  const drillToServiceArea = (area) => {
    const next = { ...filters, service_revenue_area: area }; setFilters(next); setPage(0); setActiveTab('details'); loadRecords(next, 0);
  };

  const openRecord = async (id) => {
    try { setSelectedRecord(await ontTruckRollService.getRecordDetail(id)); }
    catch (e) { console.error(e); }
  };

  /**
   * Server-side CSV export — calls the backend /export endpoint.
   * Downloads all records matching the current filters (not just the current page).
   * Admin JWT is sent in the Authorization header; Snowflake credentials stay on the server.
   */
  const handleExportCSV = async () => {
    setExportingCSV(true);
    setExportError('');
    try {
      const cleanFilters = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
      await ontTruckRollService.exportCSV(cleanFilters);
    } catch (e) {
      setExportError(e.message || 'Export failed. Please try again.');
    } finally {
      setExportingCSV(false);
    }
  };

  const kpi = data.kpi;
  const overallCortex = (data.cortex || []).find((c) => c.SUMMARY_TYPE === 'OVERALL');

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen">
        <Header />
        <main className="p-6 md:p-8 flex-1">
          <div className="max-w-[1400px] mx-auto space-y-6">

            {/* Page Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6 gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#00ABE4] to-blue-700 text-white flex items-center justify-center shadow-md flex-shrink-0">
                  <Truck className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center flex-wrap gap-2">
                    <h1 className="text-xl lg:text-2xl font-bold text-gray-800 tracking-tight">ONT Truck Roll Reporting</h1>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                      <ShieldAlert className="w-3.5 h-3.5" /> Admin Only
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm mt-0.5">Truck rolls, solutions, trends, service areas, weather correlation, and data quality — full drill-down to every source record.</p>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-2 overflow-x-auto">
              <div className="flex gap-1 min-w-max">
                {TABS.map((t) => {
                  const Icon = t.icon;
                  const isActive = activeTab === t.key;
                  return (
                    <button
                      key={t.key}
                      onClick={() => setActiveTab(t.key)}
                      className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${isActive ? 'bg-[#00ABE4] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
                        }`}
                    >
                      <Icon className="w-3.5 h-3.5" /> {t.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ============ EXECUTIVE OVERVIEW ============ */}
            {activeTab === 'overview' && (
              <>
                {loading.overview && <LoadingBlock />}
                {errors.overview && <ErrorBlock message={errors.overview} />}
                {!loading.overview && kpi && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <KpiCard label="Total Truck Rolls" value={fmtNum(kpi.total_truck_rolls)} icon={Truck} color="blue" hint="RAW.ONT_TRUCK_ROLL — source rows" />
                      <KpiCard label="Unique Order Numbers" value={fmtNum(kpi.unique_order_numbers)} icon={Layers} color="indigo" hint="ORDER_NUMBER is not a unique key" />
                      <KpiCard label="Unique Service Addresses" value={fmtNum(kpi.unique_service_addresses)} icon={MapPin} color="purple" />
                      <KpiCard label="Unique Accounts" value={fmtNum(kpi.unique_accounts)} icon={Users} color="emerald" />
                      <KpiCard label="ONT Replacements" value={fmtNum(kpi.ont_replaced_count)} icon={Wrench} color="blue" />
                      <KpiCard label="Wall Wart Replacements" value={fmtNum(kpi.wall_wart_replaced_count)} icon={Wrench} color="purple" />
                      <KpiCard label="Controller Replacements" value={fmtNum(kpi.controller_replaced_count)} icon={Wrench} color="amber" />
                      <KpiCard label="Avg Resolution Time" value={kpi.avg_resolution_hours ? `${kpi.avg_resolution_hours.toFixed(2)}h` : '—'} icon={TrendingUp} color="blue" />
                      <KpiCard label="Median Resolution Time" value={kpi.median_resolution_hours ? `${kpi.median_resolution_hours.toFixed(2)}h` : '—'} icon={TrendingUp} color="indigo" />
                      <KpiCard label="Earliest Incident" value={kpi.earliest_entered_date ? new Date(kpi.earliest_entered_date).toLocaleDateString() : '—'} icon={Calendar} color="blue" />
                      <KpiCard label="Latest Incident" value={kpi.latest_entered_date ? new Date(kpi.latest_entered_date).toLocaleDateString() : '—'} icon={Calendar} color="blue" />
                      <KpiCard label="Repeat Addresses (3+)" value={fmtNum(kpi.repeat_addresses_3plus)} icon={RotateCcw} color="amber" hint={`${fmtNum(kpi.truck_rolls_at_repeat_addresses_3plus)} truck rolls`} />
                      <KpiCard label="Exact Weather Coverage" value={fmtNum(kpi.exact_weather_count)} icon={Cloud} color="emerald" hint={kpi.total_truck_rolls ? fmtPct((kpi.exact_weather_count / kpi.total_truck_rolls) * 100) : ''} />
                      <KpiCard label="Approximate Weather Coverage" value={fmtNum(kpi.approximate_weather_count)} icon={Cloud} color="amber" hint={kpi.total_truck_rolls ? fmtPct((kpi.approximate_weather_count / kpi.total_truck_rolls) * 100) : ''} />
                      <KpiCard label="No Weather Coverage" value={fmtNum(kpi.no_weather_count)} icon={AlertTriangle} color="red" />
                      <KpiCard label="Duplicate Order # Rows" value={fmtNum(kpi.duplicate_order_number_row_count)} icon={AlertTriangle} color="red" hint="Order 586374 — preserved, not deduplicated" />
                    </div>
                    <p className="text-[11px] text-gray-400">Source: {kpi.source}</p>

                    {overallCortex && (
                      <SectionCard title="AI Summary — Overall" subtitle={`Model: ${overallCortex.MODEL_USED} · Generated ${fmtDate(overallCortex.GENERATED_AT)}`} icon={Sparkles}>
                        <p className="text-sm text-gray-700 leading-relaxed">{overallCortex.SUMMARY_TEXT}</p>
                      </SectionCard>
                    )}
                  </>
                )}
              </>
            )}

            {/* ============ TRUCK ROLL DETAILS ============ */}
            {activeTab === 'details' && (
              <SectionCard
                title="Truck Roll Details"
                subtitle={data.records ? `${fmtNum(data.records.total_count)} matching record(s)` : ''}
                icon={Table2}
                right={
                  <div className="flex items-center gap-2 flex-wrap">
                    {exportError && <span className="text-xs text-red-500">{exportError}</span>}
                    <button
                      onClick={handleExportCSV}
                      disabled={exportingCSV}
                      className="flex items-center gap-1.5 bg-[#00ABE4] hover:bg-blue-600 disabled:opacity-60 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
                      title={`Export all ${data.records?.total_count ?? ''} filtered records to CSV`}
                    >
                      {exportingCSV
                        ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Exporting…</>
                        : <><Download className="w-3.5 h-3.5" /> Export All (CSV)</>}
                    </button>
                  </div>
                }
              >
                {/* Filters */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mb-4">
                  <div className="relative col-span-2 lg:col-span-2">
                    <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
                    <input placeholder="Search account, address, order #" value={filters.search}
                      onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                      className="w-full pl-8 pr-2 py-2 text-xs border border-gray-200 rounded-lg" />
                  </div>
                  <input type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2" placeholder="From" />
                  <input type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2" placeholder="To" />
                  <select value={filters.solution} onChange={(e) => setFilters({ ...filters, solution: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2">
                    <option value="">All Solutions</option>
                    <option value="Replaced Ont">Replaced Ont</option>
                    <option value="Replaced Wall Wart">Replaced Wall Wart</option>
                    <option value="Replaced Controller">Replaced Controller</option>
                  </select>
                  <input placeholder="City" value={filters.service_city} onChange={(e) => setFilters({ ...filters, service_city: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2" />
                  <input placeholder="Service Area" value={filters.service_revenue_area} onChange={(e) => setFilters({ ...filters, service_revenue_area: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2" />
                  <input placeholder="Technician" value={filters.technician} onChange={(e) => setFilters({ ...filters, technician: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2" />
                  <select value={filters.weather_match_status} onChange={(e) => setFilters({ ...filters, weather_match_status: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2">
                    <option value="">All Weather Match</option>
                    <option value="MATCHED">Exact</option>
                    <option value="AREA_CENTROID_APPROXIMATE">Approx. (Area)</option>
                    <option value="CITY_CENTROID_APPROXIMATE">Approx. (City)</option>
                    <option value="GEOCODE_FAILED">No Location</option>
                  </select>
                  <select value={filters.location_match_type} onChange={(e) => setFilters({ ...filters, location_match_type: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2">
                    <option value="">All Location Match</option>
                    <option value="EXACT">Exact</option>
                    <option value="AREA_CENTROID">Area Centroid</option>
                    <option value="CITY_CENTROID">City Centroid</option>
                    <option value="FAILED">Failed</option>
                  </select>
                  <select value={filters.order_status} onChange={(e) => setFilters({ ...filters, order_status: e.target.value })} className="text-xs border border-gray-200 rounded-lg px-2 py-2">
                    <option value="">All Order Status</option>
                    <option value="Updated">Updated</option>
                  </select>
                  <div className="flex gap-2 col-span-2 lg:col-span-1">
                    <button onClick={applyFilters} className="flex-1 bg-[#00ABE4] hover:bg-blue-600 text-white text-xs font-semibold rounded-lg px-3 py-2">Apply</button>
                    {filtersActive && <button onClick={resetFilters} className="text-xs font-semibold text-gray-500 border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50">Reset</button>}
                  </div>
                </div>
                {filtersActive && <p className="text-[11px] text-amber-600 mb-3 flex items-center gap-1"><Info className="w-3 h-3" /> Filters active — showing a subset of {fmtNum(data.records?.total_count)} of 3,040 total records.</p>}

                {loading.details && <LoadingBlock />}
                {errors.details && <ErrorBlock message={errors.details} />}
                {!loading.details && data.records && data.records.records.length === 0 && <EmptyState />}
                {!loading.details && data.records && data.records.records.length > 0 && (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-gray-600 min-w-[1100px]">
                        <thead className="bg-gray-50 text-[11px] uppercase font-semibold text-gray-500">
                          <tr>
                            <th className="py-2 px-3">ID</th><th className="py-2 px-3">Order #</th><th className="py-2 px-3">Account</th>
                            <th className="py-2 px-3">Entered Date</th><th className="py-2 px-3">Solution</th><th className="py-2 px-3">Address</th>
                            <th className="py-2 px-3">City</th><th className="py-2 px-3">Technician</th><th className="py-2 px-3">Res. (h)</th>
                            <th className="py-2 px-3">Weather</th><th className="py-2 px-3">Flags</th><th className="py-2 px-3"></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {data.records.records.map((r) => (
                            <tr key={r.ONT_TRUCK_ROLL_ID} className="hover:bg-gray-50/80 cursor-pointer" onClick={() => openRecord(r.ONT_TRUCK_ROLL_ID)}>
                              <td className="py-2.5 px-3 font-mono">{r.ONT_TRUCK_ROLL_ID}</td>
                              <td className="py-2.5 px-3">{r.ORDER_NUMBER}</td>
                              <td className="py-2.5 px-3 font-medium text-gray-900 max-w-[140px] truncate">{r.ACCOUNT}</td>
                              <td className="py-2.5 px-3 whitespace-nowrap">{fmtDate(r.ENTERED_DATE)}</td>
                              <td className="py-2.5 px-3">
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{ color: SOLUTION_COLORS[r.SOLUTION] || '#64748b', backgroundColor: (SOLUTION_COLORS[r.SOLUTION] || '#64748b') + '15' }}>{r.SOLUTION}</span>
                              </td>
                              <td className="py-2.5 px-3 max-w-[160px] truncate">{r.SERVICE_ADDRESS}</td>
                              <td className="py-2.5 px-3">{r.SERVICE_CITY}</td>
                              <td className="py-2.5 px-3">{r.SOLUTION_ENTRY_USER}</td>
                              <td className="py-2.5 px-3">{r.RESOLUTION_HOURS != null ? Number(r.RESOLUTION_HOURS).toFixed(2) : '—'}</td>
                              <td className="py-2.5 px-3"><WeatherMatchBadge status={r.WEATHER_MATCH_STATUS} /></td>
                              <td className="py-2.5 px-3">
                                {r.IS_DUPLICATE_ORDER_NUMBER && <span title="Duplicate order number" className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />}
                                {r.IS_DATE_ANOMALY && <span title="Date anomaly" className="inline-block w-2 h-2 rounded-full bg-amber-500" />}
                              </td>
                              <td className="py-2.5 px-3"><ChevronRight className="w-3.5 h-3.5 text-gray-300" /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="flex items-center justify-between mt-4 text-xs text-gray-500">
                      <span>Page {page + 1} of {Math.max(1, Math.ceil(data.records.total_count / pageSize))} — showing {data.records.records.length} of {fmtNum(data.records.total_count)}</span>
                      <div className="flex gap-2">
                        <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))} className="p-1.5 border border-gray-200 rounded-lg disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
                        <button disabled={(page + 1) * pageSize >= data.records.total_count} onClick={() => setPage((p) => p + 1)} className="p-1.5 border border-gray-200 rounded-lg disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
                      </div>
                    </div>
                  </>
                )}
              </SectionCard>
            )}



            {/* ============ TIME TRENDS ============ */}
            {activeTab === 'trends' && (
              <>
                {loading.trends && <LoadingBlock />}
                {errors.trends && <ErrorBlock message={errors.trends} />}
                {!loading.trends && data.trends && (
                  <div className="space-y-6">
                    <SectionCard title="Monthly Truck Roll Volume" subtitle="By solution type" icon={TrendingUp}>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={data.trends} margin={{ top: 10, right: 10, left: -15, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="ENTERED_YEAR_MONTH" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                            <YAxis axisLine={false} tickLine={false} />
                            <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '10px', border: 'none', color: '#fff' }} />
                            <Legend />
                            <Bar dataKey="ONT_COUNT" name="Replaced Ont" stackId="a" fill={SOLUTION_COLORS['Replaced Ont']} />
                            <Bar dataKey="WALL_WART_COUNT" name="Replaced Wall Wart" stackId="a" fill={SOLUTION_COLORS['Replaced Wall Wart']} />
                            <Bar dataKey="CONTROLLER_COUNT" name="Replaced Controller" stackId="a" fill={SOLUTION_COLORS['Replaced Controller']} radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </SectionCard>
                    <SectionCard title="Average Resolution Time Trend" icon={TrendingUp}>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={data.trends} margin={{ top: 10, right: 10, left: -15, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="ENTERED_YEAR_MONTH" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                            <YAxis axisLine={false} tickLine={false} unit="h" />
                            <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '10px', border: 'none', color: '#fff' }} />
                            <Line type="monotone" dataKey="AVG_RESOLUTION_HOURS" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </SectionCard>
                  </div>
                )}
              </>
            )}

            {/* ============ LOCATION / SERVICE AREA ============ */}
            {activeTab === 'location' && (
              <>
                {loading.location && <LoadingBlock />}
                {errors.location && <ErrorBlock message={errors.location} />}
                {!loading.location && data.location && (
                  <SectionCard title="Truck Rolls by Service Area" subtitle={`${data.location.length} area/city combinations`} icon={MapPin}>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm text-gray-600">
                        <thead className="bg-gray-50 text-xs uppercase font-semibold text-gray-500">
                          <tr><th className="py-2.5 px-3">Service Revenue Area</th><th className="py-2.5 px-3">City</th><th className="py-2.5 px-3">Truck Rolls</th><th className="py-2.5 px-3">Avg Resolution (h)</th><th className="py-2.5 px-3"></th></tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {data.location.map((a, i) => (
                            <tr key={i} className="hover:bg-gray-50/80 cursor-pointer" onClick={() => drillToServiceArea(a.SERVICE_REVENUE_AREA)}>
                              <td className="py-2.5 px-3 font-semibold text-gray-900">{a.SERVICE_REVENUE_AREA}</td>
                              <td className="py-2.5 px-3">{a.SERVICE_CITY}</td>
                              <td className="py-2.5 px-3">{fmtNum(a.TRUCK_ROLL_COUNT)}</td>
                              <td className="py-2.5 px-3">{a.AVG_RESOLUTION_HOURS}</td>
                              <td className="py-2.5 px-3"><ChevronRight className="w-4 h-4 text-gray-300" /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </SectionCard>
                )}
              </>
            )}

            {/* ============ REPEAT ADDRESSES ============ */}
            {activeTab === 'repeat' && (
              <>
                {loading.repeat && <LoadingBlock />}
                {errors.repeat && <ErrorBlock message={errors.repeat} />}
                {!loading.repeat && data.repeat && (() => {
                  const addr1 = data.repeat.filter((a) => a.TRUCK_ROLL_COUNT === 1).length;
                  const addr2 = data.repeat.filter((a) => a.TRUCK_ROLL_COUNT === 2).length;
                  const addr3plus = data.repeat.filter((a) => a.IS_REPEAT_ADDRESS_3PLUS);
                  const rolls3plus = addr3plus.reduce((s, a) => s + a.TRUCK_ROLL_COUNT, 0);
                  return (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <KpiCard label="Total Addresses" value={fmtNum(data.repeat.length)} icon={MapPin} color="blue" />
                        <KpiCard label="1 Truck Roll" value={fmtNum(addr1)} icon={MapPin} color="emerald" />
                        <KpiCard label="2 Truck Rolls" value={fmtNum(addr2)} icon={MapPin} color="amber" />
                        <KpiCard label="3+ Truck Rolls" value={fmtNum(addr3plus.length)} icon={RotateCcw} color="red" hint={`${fmtNum(rolls3plus)} truck rolls`} />
                      </div>
                      <SectionCard title="Repeat Addresses (3+ Truck Rolls)" subtitle="Click an address to see every associated event" icon={RotateCcw}>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs text-gray-600 min-w-[900px]">
                            <thead className="bg-gray-50 text-[11px] uppercase font-semibold text-gray-500">
                              <tr>
                                <th className="py-2 px-3">Address</th><th className="py-2 px-3">City</th><th className="py-2 px-3">Area</th>
                                <th className="py-2 px-3">Count</th><th className="py-2 px-3">First</th><th className="py-2 px-3">Last</th>
                                <th className="py-2 px-3">ONT</th><th className="py-2 px-3">Wall Wart</th><th className="py-2 px-3">Controller</th><th className="py-2 px-3">Avg Res (h)</th><th></th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {addr3plus.map((a, i) => (
                                <tr key={i} className="hover:bg-gray-50/80 cursor-pointer" onClick={() => drillToAddress(a.SERVICE_ADDRESS)}>
                                  <td className="py-2.5 px-3 font-medium text-gray-900">{a.SERVICE_ADDRESS}</td>
                                  <td className="py-2.5 px-3">{a.SERVICE_CITY}</td>
                                  <td className="py-2.5 px-3">{a.SERVICE_REVENUE_AREA}</td>
                                  <td className="py-2.5 px-3 font-bold">{a.TRUCK_ROLL_COUNT}</td>
                                  <td className="py-2.5 px-3">{new Date(a.FIRST_TRUCK_ROLL_DATE).toLocaleDateString()}</td>
                                  <td className="py-2.5 px-3">{new Date(a.LAST_TRUCK_ROLL_DATE).toLocaleDateString()}</td>
                                  <td className="py-2.5 px-3">{a.ONT_COUNT}</td><td className="py-2.5 px-3">{a.WALL_WART_COUNT}</td><td className="py-2.5 px-3">{a.CONTROLLER_COUNT}</td>
                                  <td className="py-2.5 px-3">{a.AVG_RESOLUTION_HOURS}</td>
                                  <td className="py-2.5 px-3"><ChevronRight className="w-3.5 h-3.5 text-gray-300" /></td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </SectionCard>
                    </div>
                  );
                })()}
              </>
            )}

            {/* ============ TECHNICIAN ANALYSIS ============ */}
            {activeTab === 'technician' && (
              <>
                {loading.technician && <LoadingBlock />}
                {errors.technician && <ErrorBlock message={errors.technician} />}
                {!loading.technician && data.technician && (
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div className="lg:col-span-7 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6">
                      <h3 className="text-base font-bold text-gray-900 mb-4">Technician Workload</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-gray-600">
                          <thead className="bg-gray-50 text-xs uppercase font-semibold text-gray-500">
                            <tr><th className="py-2.5 px-3">Rank</th><th className="py-2.5 px-3">Technician</th><th className="py-2.5 px-3">Truck Rolls</th><th className="py-2.5 px-3">Avg Res (h)</th><th></th></tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {data.technician.map((t, i) => (
                              <tr key={i} className="hover:bg-gray-50/80 cursor-pointer" onClick={() => drillToTechnician(t.SOLUTION_ENTRY_USER)}>
                                <td className="py-3 px-3"><span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${i === 0 ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-600'}`}>#{i + 1}</span></td>
                                <td className="py-3 px-3 font-semibold text-gray-900">{t.SOLUTION_ENTRY_USER}</td>
                                <td className="py-3 px-3">{fmtNum(t.TRUCK_ROLL_COUNT)}</td>
                                <td className="py-3 px-3">{t.AVG_RESOLUTION_HOURS}</td>
                                <td className="py-3 px-3"><ChevronRight className="w-4 h-4 text-gray-300" /></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                    <div className="lg:col-span-5 bg-white rounded-xl shadow-sm border border-gray-200 p-5 lg:p-6">
                      <h3 className="text-base font-bold text-gray-900 mb-4">Top 10 by Volume</h3>
                      <div className="h-96">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={data.technician.slice(0, 10)} layout="vertical" margin={{ left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                            <XAxis type="number" axisLine={false} tickLine={false} />
                            <YAxis type="category" dataKey="SOLUTION_ENTRY_USER" tick={{ fontSize: 10 }} width={90} axisLine={false} tickLine={false} />
                            <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '10px', border: 'none', color: '#fff' }} />
                            <Bar dataKey="TRUCK_ROLL_COUNT" fill="#00ABE4" radius={[0, 6, 6, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ============ WEATHER ANALYSIS ============ */}
            {activeTab === 'weather' && (
              <>
                {loading.weather && <LoadingBlock />}
                {errors.weather && <ErrorBlock message={errors.weather} />}
                {!loading.weather && data.weather && (() => {
                  const buckets = data.weather.location_buckets || [];
                  const exact = buckets.filter((b) => b.BUCKET === 'EXACT');
                  const approx = buckets.filter((b) => b.BUCKET === 'APPROXIMATE');
                  const exactN = exact.reduce((s, b) => s + b.N, 0);
                  const approxN = approx.reduce((s, b) => s + b.N, 0);
                  const exactPrecip = exact.reduce((s, b) => s + b.WITH_PRECIP, 0);
                  const approxPrecip = approx.reduce((s, b) => s + b.WITH_PRECIP, 0);
                  const total = exactN + approxN;
                  const conditions = data.weather.weather_conditions || [];
                  return (
                    <div className="space-y-6">
                      <div className="bg-blue-50 border border-blue-200 text-blue-800 text-xs px-4 py-3 rounded-lg flex items-start gap-2">
                        <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
                        <span>Approximate weather (area/city centroid) is <strong>not</strong> the same as weather measured at the exact service address. Figures below are shown separately for this reason.</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="bg-white rounded-xl shadow-sm border border-emerald-200 p-5">
                          <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">Exact Weather</p>
                          <h3 className="text-3xl font-bold text-gray-900 mt-1">{fmtNum(exactN)} <span className="text-base font-medium text-gray-400">({total ? fmtPct((exactN / total) * 100) : '—'})</span></h3>
                          <p className="text-xs text-gray-500 mt-2">{fmtNum(exactPrecip)} truck rolls occurred during periods with measurable precipitation ({exactN ? fmtPct((exactPrecip / exactN) * 100) : '—'}).</p>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border border-amber-200 p-5">
                          <p className="text-xs font-semibold text-amber-700 uppercase tracking-wider">Approximate Weather (Area/City)</p>
                          <h3 className="text-3xl font-bold text-gray-900 mt-1">{fmtNum(approxN)} <span className="text-base font-medium text-gray-400">({total ? fmtPct((approxN / total) * 100) : '—'})</span></h3>
                          <p className="text-xs text-gray-500 mt-2">{fmtNum(approxPrecip)} truck rolls occurred during periods with measurable precipitation ({approxN ? fmtPct((approxPrecip / approxN) * 100) : '—'}) — based on area/city average location.</p>
                        </div>
                      </div>
                      <SectionCard title="Weather Condition Distribution" subtitle="Split by exact vs. approximate location match" icon={Cloud}>
                        <div className="h-80">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={Object.values(conditions.reduce((acc, c) => {
                              acc[c.WEATHER_CONDITION] = acc[c.WEATHER_CONDITION] || { condition: c.WEATHER_CONDITION, EXACT: 0, APPROXIMATE: 0 };
                              acc[c.WEATHER_CONDITION][c.BUCKET] = c.N;
                              return acc;
                            }, {}))} margin={{ top: 10, right: 10, left: -15, bottom: 5 }}>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                              <XAxis dataKey="condition" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                              <YAxis axisLine={false} tickLine={false} />
                              <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '10px', border: 'none', color: '#fff' }} />
                              <Legend />
                              <Bar dataKey="EXACT" name="Exact" fill="#10b981" radius={[4, 4, 0, 0]} />
                              <Bar dataKey="APPROXIMATE" name="Approximate" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </SectionCard>
                      <p className="text-[11px] text-gray-400">Language note: figures describe when truck rolls <em>occurred during</em> certain weather conditions — this is an observation of co-occurrence, not a claim that weather caused the truck roll.</p>
                    </div>
                  );
                })()}
              </>
            )}



            {/* ============ CORTEX AI SUMMARIES ============ */}
            {activeTab === 'cortex' && (
              <>
                {loading.cortex && <LoadingBlock />}
                {errors.cortex && <ErrorBlock message={errors.cortex} />}
                {!loading.cortex && data.cortexFull && (
                  <div className="space-y-5">
                    {data.cortexFull.length === 0 && <EmptyState message="No Cortex summaries have been generated yet." />}
                    {data.cortexFull.map((c, i) => (
                      <SectionCard
                        key={i}
                        title={c.SUMMARY_TYPE.replace(/_/g, ' ')}
                        subtitle={`Model: ${c.MODEL_USED || '—'} · Status: ${c.GENERATION_STATUS} · Last Generated: ${fmtDate(c.GENERATED_AT)}`}
                        icon={Sparkles}
                        right={c.GENERATION_STATUS === 'SUCCESS' ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <AlertCircle className="w-4 h-4 text-red-500" />}
                      >
                        <p className="text-sm text-gray-700 leading-relaxed">{c.SUMMARY_TEXT || 'No summary text available.'}</p>
                      </SectionCard>
                    ))}
                    <p className="text-[11px] text-gray-400">Summaries are pre-generated from validated SQL aggregates (never live row-level data) and persisted in ANALYTICS.CORTEX_SUMMARIES — this page reads the latest stored summary of each type, it does not call Cortex on page load.</p>
                  </div>
                )}
              </>
            )}

          </div>
        </main>
      </div>
      <RecordDetailModal record={selectedRecord} onClose={() => setSelectedRecord(null)} />
    </div>
  );
};

export default AdminOntTruckRoll;
