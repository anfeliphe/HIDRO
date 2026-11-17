import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Database, Map, Upload, Download, AlertCircle } from 'lucide-react';
import * as api from '../api/client';

const DataSources = () => {
  const [uploadFile, setUploadFile] = useState(null);
  const [replaceAll, setReplaceAll] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [parcelTotal, setParcelTotal] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    api.getParcels('All', 0, 1).then((r) => setParcelTotal(r.total ?? null)).catch(() => setParcelTotal(null));
  }, [uploadResult]);

  const dataSources = [
    {
      name: "Datos de predios",
      status: "Activo",
      type: "Predios (SIG / CSV / carga)",
      records: parcelTotal != null ? `${parcelTotal} predios` : '—',
      updated: "Según la carga",
      icon: Map,
      color: 'blue',
    },
    {
      name: "Demanda estimada",
      status: "Activo",
      type: "Modelo (0,09 / 0,1 m³ por persona al día)",
      records: "A partir de los predios",
      updated: "Al consultar",
      icon: Database,
      color: 'purple',
      description: "La demanda se estima según los habitantes y el uso del predio.",
    },
    {
      name: "Mapa base de OpenStreetMap",
      status: "Conectado",
      type: "Servicio de mapas",
      records: "En línea",
      updated: "En línea",
      icon: Map,
      color: 'orange',
    },
  ];

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    setUploadFile(f || null);
    setUploadResult(null);
    setUploadError(null);
  };

  const handleUpload = async () => {
    if (!uploadFile) {
      setUploadError("Selecciona un archivo.");
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    try {
      const review = await api.uploadParcelDataset(uploadFile, replaceAll, true);
      if(review.warnings?.length&&!window.confirm('Revisa antes de importar:\n\n'+review.warnings.join('\n')+'\n\n¿Deseas continuar?'))return;
      const result = await api.uploadParcelDataset(uploadFile, replaceAll, false, review.review_token);
      setUploadResult(result);
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setUploadError(err.message || "No se pudo cargar el archivo");
    } finally {
      setUploading(false);
    }
  };

  const getStatusColor = (status) => {
    if (status === "Activo" || status === "Conectado") {
      return 'bg-green-100 text-green-800';
    }
    return 'bg-gray-100 text-gray-800';
  };

  const getIconColor = (color) => {
    const colors = {
      blue: 'bg-blue-100 text-blue-600',
      green: 'bg-green-100 text-green-600',
      purple: 'bg-purple-100 text-purple-600',
      orange: 'bg-orange-100 text-orange-600',
    };
    return colors[color] || colors.blue;
  };

  const sampleCsv = `parcel_id,land_use,population,lat,lng
P-0001,Residential,4,40.7128,-74.006
P-0002,Commercial,12,40.713,-74.005
P-0003,Mixed-use,6,40.714,-74.004`;

  const handleDownloadSample = () => {
    const blob = new Blob([sampleCsv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'HIDRO_predios_ejemplo.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 sm:px-6 pt-6 pb-4 bg-white/90 backdrop-blur-md border-b border-gray-200/60 lg:pl-6 pl-16 animate-fade-in">
        <h2 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
          Fuentes de datos
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        {/* Upload parcel dataset */}
        <div
          className="card-gradient mb-6 sm:mb-8 p-5 sm:p-6 opacity-0 animate-fade-in-up"
          style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-lg bg-indigo-100 text-indigo-600">
              <Upload size={24} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Importar datos de predios</h3>
              <p className="text-sm text-gray-600 mt-0.5">
                Importa predios desde CSV, JSON o GeoJSON. El mapa y los análisis usarán estos datos.
              </p>
            </div>
          </div>
          <div className="space-y-4 pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.json,.geojson"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer sm:whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={replaceAll}
                  onChange={(e) => setReplaceAll(e.target.checked)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                Reemplazar todos los predios anteriores
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleUpload}
                disabled={uploading || !uploadFile}
                className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Cargando…
                  </>
                ) : (
                  <>
                    <Upload size={18} />
                    Cargar archivo
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={handleDownloadSample}
                className="btn-secondary flex items-center gap-2"
              >
                <Download size={18} />
                Descargar CSV de ejemplo
              </button>
            </div>
            {uploadError && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 text-red-800 text-sm">
                <AlertCircle size={18} className="shrink-0 mt-0.5" />
                <span>{uploadError}</span>
              </div>
            )}
            {uploadResult && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-green-50 text-green-800 text-sm">
                <CheckCircle2 size={18} className="shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">{uploadResult.message}</p>
                  {uploadResult.errors?.length > 0 && (
                    <ul className="mt-1 list-disc list-inside text-xs opacity-90">
                      {uploadResult.errors.slice(0, 5).map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                      {uploadResult.errors.length > 5 && (
                        <li>… y {uploadResult.errors.length - 5} más</li>
                      )}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-4 pt-4 border-t border-gray-200">
            Columnas obligatorias: <code className="bg-gray-100 px-1 rounded">parcel_id</code>,{' '}
            <code className="bg-gray-100 px-1 rounded">land_use</code> (Residential | Commercial | Mixed-use),{' '}
            <code className="bg-gray-100 px-1 rounded">population</code>,{' '}
            <code className="bg-gray-100 px-1 rounded">lat</code>,{' '}
            <code className="bg-gray-100 px-1 rounded">lng</code>. En GeoJSON utiliza <code className="bg-gray-100 px-1 rounded">properties</code> y, opcionalmente, una geometría de punto (Point) en <code className="bg-gray-100 px-1 rounded">geometry</code> para la latitud y longitud.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 max-w-6xl mx-auto">
          {dataSources.map((source, index) => {
            const Icon = source.icon;
            return (
              <div
                key={index}
                className="card-gradient opacity-0 animate-fade-in-up hover:shadow-xl transition-shadow duration-300"
                style={{ animationDelay: `${(index + 1) * 80}ms`, animationFillMode: 'forwards' }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-lg ${getIconColor(source.color)}`}>
                      <Icon size={24} />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{source.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">{source.type}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(source.status)}`}>
                    {source.status}
                  </span>
                </div>

                <div className="space-y-2 pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Registros:</span>
                    <span className="font-medium text-gray-900">{source.records}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Actualización:</span>
                    <span className="font-medium text-gray-900">{source.updated}</span>
                  </div>
                  {source.description && (
                    <p className="text-xs text-gray-500 pt-2">{source.description}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DataSources;
