from aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.quality_inspection.quality_inspection import (
    QualityInspection
)

class AQLInspection(QualityInspection):

    def get_indicator(self):
        if self.status == "Accepted":
            return ("Accepted", "green")