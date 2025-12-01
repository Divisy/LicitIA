import React, { useState, useEffect } from 'react'
import { 
  FileUploader, 
  FileUploaderItem,
  Button,
  InlineNotification,
  Loading,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Accordion,
  AccordionItem
} from '@carbon/react'
import { DocumentAdd, Upload, Download, Add } from '@carbon/icons-react'
import { importExperiences } from '../api/client'
import ExperienceManualForm from './ExperienceManualForm'
import './ExperienceUpload.scss'

interface ExperienceUploadProps {
  onUploadSuccess?: (count?: number) => void
  defaultCompanyName?: string
  showValueProposition?: boolean
}

const ExperienceUpload: React.FC<ExperienceUploadProps> = ({ 
  onUploadSuccess, 
  defaultCompanyName = 'BEC',
  showValueProposition = true
}) => {
  const [file, setFile] = useState<File | null>(null)
  const [companyName, setCompanyName] = useState<string>(defaultCompanyName)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [activeTab, setActiveTab] = useState(0)

  useEffect(() => {
    setCompanyName(defaultCompanyName)
  }, [defaultCompanyName])

  const handleFileChange = (event: { target: { files: FileList | null } }) => {
    const selectedFile = event.target.files?.[0]
    if (!selectedFile) return

    if (!selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls')) {
      setMessage({ type: 'error', text: 'Por favor selecciona un archivo Excel (.xlsx o .xls)' })
      setFile(null)
      return
    }
    
    setFile(selectedFile)
    setMessage(null)
  }

  const handleRemoveFile = () => {
    setFile(null)
    setMessage(null)
  }

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Por favor selecciona un archivo' })
      return
    }

    if (!companyName.trim()) {
      setMessage({ type: 'error', text: 'Por favor ingresa el nombre de la empresa' })
      return
    }

    setUploading(true)
    setMessage(null)

    try {
      const result = await importExperiences(file, companyName.trim())
      
      if (result.errors && result.errors.length > 0) {
        const errorText = result.errors.length > 3 
          ? `${result.errors.slice(0, 3).join(', ')}... (${result.errors.length} errores totales)`
          : result.errors.join(', ')
        setMessage({
          type: 'error',
          text: `${result.message}. Errores: ${errorText}`
        })
      } else {
        setMessage({ type: 'success', text: result.message })
        setFile(null)
        
        if (onUploadSuccess) {
          onUploadSuccess(result.imported)
        }
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Error al subir el archivo'
      })
    } finally {
      setUploading(false)
    }
  }

  const handleManualSuccess = (count: number) => {
    if (onUploadSuccess) {
      onUploadSuccess(count)
    }
  }

  const handleDownloadTemplate = () => {
    // Download template from public folder
    const link = document.createElement('a')
    link.href = '/plantilla-experiencias.xlsx'
    link.download = 'plantilla-experiencias.xlsx'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleUseExampleTemplate = async () => {
    // Load example template and automatically upload it
    try {
      const response = await fetch('/plantilla-ejemplo-experiencias.xlsx')
      if (!response.ok) {
        throw new Error('No se pudo cargar la plantilla de ejemplo')
      }
      
      const blob = await response.blob()
      const exampleFile = new File([blob], 'plantilla-ejemplo-experiencias.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      
      setFile(exampleFile)
      setMessage({
        type: 'success',
        text: 'Plantilla de ejemplo cargada. Haz clic en "Subir Experiencias" para ver cómo funcionan los matches.'
      })
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Error al cargar la plantilla de ejemplo'
      })
    }
  }

  return (
    <div className="experience-upload">
      {/* Simple Tabs */}
      <div className="experience-upload__tabs">
        <button
          className={`experience-upload__tab ${activeTab === 0 ? 'experience-upload__tab--active' : ''}`}
          onClick={() => setActiveTab(0)}
        >
          <DocumentAdd size={20} />
          <span>Desde Excel</span>
        </button>
        <button
          className={`experience-upload__tab ${activeTab === 1 ? 'experience-upload__tab--active' : ''}`}
          onClick={() => setActiveTab(1)}
        >
          <Add size={20} />
          <span>Manual</span>
        </button>
      </div>

      {/* Content Panels */}
      <div className="experience-upload__content">
        {activeTab === 0 && (
          <div className="experience-upload__excel-section">
            {uploading ? (
              <div className="experience-upload-loading">
                <Loading description="Subiendo archivo..." withOverlay={false} />
                <p className="experience-upload-loading-text">Procesando archivo...</p>
              </div>
            ) : (
              <>
                <div className="experience-upload__dropzone">
                  <FileUploader
                    accept={['.xlsx', '.xls']}
                    buttonKind="primary"
                    buttonLabel="Seleccionar archivo Excel"
                    filenameStatus="edit"
                    iconDescription="Eliminar archivo"
                    labelDescription="Solo archivos .xlsx o .xls"
                    labelTitle=""
                    multiple={false}
                    onChange={handleFileChange}
                    size="lg"
                    className="experience-upload-file-uploader"
                  />
                  {!file && (
                    <p className="experience-upload__dropzone-hint">
                      Arrastra y suelta tu archivo aquí o haz clic para seleccionar
                    </p>
                  )}
                </div>

                {file && (
                  <div className="experience-upload-file-list">
                    <FileUploaderItem
                      name={file.name}
                      status="complete"
                      onDelete={handleRemoveFile}
                      size={file.size}
                    />
                  </div>
                )}

                {message && (
                  <InlineNotification
                    kind={message.type === 'success' ? 'success' : 'error'}
                    title={message.type === 'success' ? '¡Éxito!' : 'Error'}
                    subtitle={message.text}
                    lowContrast={false}
                    className="experience-upload-message"
                    onClose={() => setMessage(null)}
                  />
                )}

                <div className="experience-upload__actions">
                  <div className="experience-upload__template-buttons">
                    <Button
                      kind="ghost"
                      size="md"
                      onClick={handleDownloadTemplate}
                      renderIcon={Download}
                      className="experience-upload-template-button"
                    >
                      Descargar Plantilla
                    </Button>
                    <Button
                      kind="tertiary"
                      size="md"
                      onClick={handleUseExampleTemplate}
                      className="experience-upload-example-button"
                    >
                      Usar Plantilla de Ejemplo
                    </Button>
                  </div>
                  <Button
                    type="button"
                    size="lg"
                    onClick={handleUpload}
                    disabled={!file || uploading || !companyName.trim()}
                    renderIcon={Upload}
                    className="experience-upload-button"
                  >
                    {uploading ? 'Subiendo...' : 'Subir Experiencias'}
                  </Button>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 1 && (
          <div className="experience-upload__manual-section">
            <ExperienceManualForm
              companyName={companyName}
              onSuccess={handleManualSuccess}
            />
          </div>
        )}
      </div>

      {activeTab === 0 && (
        <div className="experience-upload-help-section">
          <Accordion className="experience-upload-help">
            <AccordionItem 
              title="Formato del archivo Excel"
              open={false}
            >
              <div className="experience-upload-help-content">
                <p className="experience-upload-help-text">
                  Tu archivo Excel debe tener estas columnas (solo <strong>OBRA</strong> es obligatoria):
                </p>
                <div className="experience-upload-help-columns">
                  <div className="experience-upload-help-column experience-upload-help-column--required">
                    <span className="experience-upload-help-column-name">OBRA *</span>
                    <span className="experience-upload-help-column-desc">Descripción del proyecto</span>
                  </div>
                  <div className="experience-upload-help-column">
                    <span className="experience-upload-help-column-name">EMPRESA</span>
                    <span className="experience-upload-help-column-desc">Nombre de la empresa</span>
                  </div>
                  <div className="experience-upload-help-column">
                    <span className="experience-upload-help-column-name">ENTIDAD CONTRATANTE</span>
                    <span className="experience-upload-help-column-desc">Entidad que contrató</span>
                  </div>
                  <div className="experience-upload-help-column">
                    <span className="experience-upload-help-column-name">VALOR ACTUAL</span>
                    <span className="experience-upload-help-column-desc">Monto del contrato</span>
                  </div>
                  <div className="experience-upload-help-column">
                    <span className="experience-upload-help-column-name">FECHA FINALIZACIÓN</span>
                    <span className="experience-upload-help-column-desc">Fecha de finalización</span>
                  </div>
                  <div className="experience-upload-help-column">
                    <span className="experience-upload-help-column-name">CONTRATO No.</span>
                    <span className="experience-upload-help-column-desc">Número de contrato</span>
                  </div>
                  <div className="experience-upload-help-column">
                    <span className="experience-upload-help-column-name">CATEGORÍA</span>
                    <span className="experience-upload-help-column-desc">Categoría del proyecto</span>
                  </div>
                  <div className="experience-upload-help-column">
                    <span className="experience-upload-help-column-name">ÁREA DE LA INGENIERÍA CIVIL</span>
                    <span className="experience-upload-help-column-desc">Área de ingeniería</span>
                  </div>
                </div>
              </div>
            </AccordionItem>
          </Accordion>
        </div>
      )}
    </div>
  )
}

export default ExperienceUpload
