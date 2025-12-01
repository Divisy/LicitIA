import React from 'react'
import { 
  Tile, 
  Button, 
  Tag,
  DataTable,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  Link
} from '@carbon/react'
import { TrashCan, Document, Building, DocumentAdd, WatsonMachineLearning } from '@carbon/icons-react'
import { CompanyExperience } from '../api/client'
import { deleteExperience } from '../api/client'
import './ExperienceList.scss'

interface ExperienceListProps {
  experiences: CompanyExperience[]
  companyName: string
  onDelete?: () => void
}

const ExperienceList: React.FC<ExperienceListProps> = ({ 
  experiences, 
  companyName, 
  onDelete 
}) => {
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString('es-CO', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      })
    } catch {
      return 'N/A'
    }
  }

  const formatCurrency = (amount: number | null): string => {
    if (!amount) return 'N/A'
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('¿Estás seguro de que deseas eliminar esta experiencia?')) {
      return
    }

    try {
      await deleteExperience(id)
      if (onDelete) {
        onDelete()
      }
    } catch (error) {
      alert('Error al eliminar la experiencia: ' + (error instanceof Error ? error.message : 'Error desconocido'))
    }
  }

  if (experiences.length === 0) {
    return (
      <div className="experience-list-empty">
        <Document size={48} className="experience-list-empty-icon" />
        <p className="experience-list-empty-text">
          No se encontraron experiencias para <strong>{companyName}</strong>.
        </p>
        <p className="experience-list-empty-hint">
          Sube un archivo Excel para comenzar.
        </p>
      </div>
    )
  }

  const getExperienceIcon = (experience: CompanyExperience) => {
    const desc = (experience.project_description || '').toLowerCase()
    const category = (experience.category || '').toLowerCase()
    const area = (experience.engineering_area || '').toLowerCase()
    
    if (desc.includes('interventoría') || desc.includes('supervisión') || category.includes('interventoría')) {
      return <WatsonMachineLearning size={20} className="experience-list-service-icon" />
    }
    if (desc.includes('construcción') || category.includes('construcción')) {
      return <Building size={20} className="experience-list-service-icon" />
    }
    return <DocumentAdd size={20} className="experience-list-service-icon" />
  }

  const headers = [
    { key: 'service', header: 'Experiencia' },
    { key: 'name', header: 'Nombre' },
    { key: 'entity', header: 'Entidad Contratante' },
    { key: 'contract', header: 'Contrato' },
    { key: 'date', header: 'Fecha Finalización' },
    { key: 'amount', header: 'Valor' },
    { key: 'category', header: 'Categoría' },
    { key: 'details', header: '' },
  ]

  const rows = experiences.map((experience) => ({
    id: experience.id,
    service: (
      <div className="experience-list-service">
        {getExperienceIcon(experience)}
        <span className="experience-list-service-name">
          {experience.category || experience.engineering_area || 'Experiencia'}
        </span>
      </div>
    ),
    name: (
      <div className="experience-list-name">
        {experience.project_description.length > 60
          ? `${experience.project_description.substring(0, 60)}...`
          : experience.project_description}
      </div>
    ),
    entity: experience.contracting_entity || 'N/A',
    contract: experience.contract_number || 'N/A',
    date: formatDate(experience.completion_date),
    amount: experience.amount ? (
      <span className="experience-list-amount">{formatCurrency(experience.amount)}</span>
    ) : 'N/A',
    category: experience.category ? (
      <Tag type="blue" size="sm">{experience.category}</Tag>
    ) : experience.engineering_area ? (
      <Tag type="cyan" size="sm">{experience.engineering_area}</Tag>
    ) : 'N/A',
    details: (
      <div className="experience-list-details">
        <Link
          href="#"
          onClick={(e) => {
            e.preventDefault()
            const details = [
              `Proyecto: ${experience.project_description}`,
              `Entidad: ${experience.contracting_entity || 'N/A'}`,
              `Contrato: ${experience.contract_number || 'N/A'}`,
              `Fecha: ${formatDate(experience.completion_date)}`,
              `Valor: ${formatCurrency(experience.amount)}`,
              `Categoría: ${experience.category || 'N/A'}`,
              `Área: ${experience.engineering_area || 'N/A'}`,
            ].join('\n')
            
            const confirmDelete = window.confirm(
              `Detalles de la experiencia:\n\n${details}\n\n¿Desea eliminar esta experiencia?`
            )
            
            if (confirmDelete) {
              handleDelete(experience.id)
            }
          }}
          className="experience-list-details-link"
        >
          Ver detalles
        </Link>
      </div>
    ),
  }))

  return (
    <div className="experience-list">
      <div className="experience-list-table-container">
        <DataTable
          rows={rows}
          headers={headers}
          isSortable
          size="md"
          useZebraStyles
        >
          {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
            <Table {...getTableProps()}>
              <TableHead>
                <TableRow>
                  {headers.map((header) => (
                    <TableHeader {...getHeaderProps({ header })} key={header.key}>
                      {header.header}
                    </TableHeader>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow {...getRowProps({ row })} key={row.id}>
                    {row.cells.map((cell) => (
                      <TableCell key={cell.id}>
                        {cell.value}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DataTable>
      </div>
    </div>
  )
}

export default ExperienceList
