/**
 * Authentic PrimeKG Knowledge Graph Dataset
 * Extracted directly from primekg_nodes.csv and primekg_edges.csv.
 * Represents verified relationships between clinical oncology compounds,
 * biological targets/enzymes, cellular pathways, and neoplastic indications.
 */

import type { KGGraph } from '../types/api';

export const PRIME_KG_SUBGRAPH: KGGraph = {
  "nodes": [
    {
      "id": "Cisplatin",
      "name": "Cisplatin",
      "type": "drug",
      "degree": 29
    },
    {
      "id": "ALB",
      "name": "ALB",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "Irinotecan",
      "name": "Irinotecan",
      "type": "drug",
      "degree": 18
    },
    {
      "id": "PTGS2",
      "name": "PTGS2",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "CYP4A11",
      "name": "CYP4A11",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "GSTM1",
      "name": "GSTM1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "GSTP1",
      "name": "GSTP1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "GSTT1",
      "name": "GSTT1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "MPO",
      "name": "MPO",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "Paclitaxel",
      "name": "Paclitaxel",
      "type": "drug",
      "degree": 22
    },
    {
      "id": "CYP1B1",
      "name": "CYP1B1",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "Docetaxel",
      "name": "Docetaxel",
      "type": "drug",
      "degree": 17
    },
    {
      "id": "NQO1",
      "name": "NQO1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "CYP19A1",
      "name": "CYP19A1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "BCHE",
      "name": "BCHE",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "XDH",
      "name": "XDH",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "Cyclophosphamide",
      "name": "Cyclophosphamide",
      "type": "drug",
      "degree": 9
    },
    {
      "id": "CYP3A5",
      "name": "CYP3A5",
      "type": "protein",
      "degree": 5
    },
    {
      "id": "Vincristine",
      "name": "Vincristine",
      "type": "drug",
      "degree": 17
    },
    {
      "id": "SOD1",
      "name": "SOD1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "CYP3A4",
      "name": "CYP3A4",
      "type": "protein",
      "degree": 6
    },
    {
      "id": "Topotecan",
      "name": "Topotecan",
      "type": "drug",
      "degree": 7
    },
    {
      "id": "CES1",
      "name": "CES1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "CYP2C9",
      "name": "CYP2C9",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "CYP2C8",
      "name": "CYP2C8",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "CYP2A6",
      "name": "CYP2A6",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "CYP2C19",
      "name": "CYP2C19",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "UGT1A9",
      "name": "UGT1A9",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "UGT1A1",
      "name": "UGT1A1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "CYP2B6",
      "name": "CYP2B6",
      "type": "protein",
      "degree": 3
    },
    {
      "id": "CYP2C18",
      "name": "CYP2C18",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "CYP3A7",
      "name": "CYP3A7",
      "type": "protein",
      "degree": 4
    },
    {
      "id": "CES2",
      "name": "CES2",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "MT1A",
      "name": "MT1A",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "MT2A",
      "name": "MT2A",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "TUBB1",
      "name": "TUBB1",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "TOP1MT",
      "name": "TOP1MT",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "TUBB",
      "name": "TUBB",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "BCL2",
      "name": "BCL2",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "TF",
      "name": "TF",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "A2M",
      "name": "A2M",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "NR1I2",
      "name": "NR1I2",
      "type": "protein",
      "degree": 3
    },
    {
      "id": "TOP1",
      "name": "TOP1",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "MAP2",
      "name": "MAP2",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "TUBA4A",
      "name": "TUBA4A",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "ATOX1",
      "name": "ATOX1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "MAPT",
      "name": "MAPT",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "MAP4",
      "name": "MAP4",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "MPG",
      "name": "MPG",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "ABCB11",
      "name": "ABCB11",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "ABCC1",
      "name": "ABCC1",
      "type": "protein",
      "degree": 4
    },
    {
      "id": "SLCO1B1",
      "name": "SLCO1B1",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "ABCB1",
      "name": "ABCB1",
      "type": "protein",
      "degree": 5
    },
    {
      "id": "ABCC3",
      "name": "ABCC3",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "ABCG2",
      "name": "ABCG2",
      "type": "protein",
      "degree": 5
    },
    {
      "id": "ABCC2",
      "name": "ABCC2",
      "type": "protein",
      "degree": 5
    },
    {
      "id": "ABCC5",
      "name": "ABCC5",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "ABCC6",
      "name": "ABCC6",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "SLC22A7",
      "name": "SLC22A7",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "SLC22A2",
      "name": "SLC22A2",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "SLC31A1",
      "name": "SLC31A1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "SLC22A3",
      "name": "SLC22A3",
      "type": "protein",
      "degree": 2
    },
    {
      "id": "ABCC10",
      "name": "ABCC10",
      "type": "protein",
      "degree": 3
    },
    {
      "id": "SLC47A1",
      "name": "SLC47A1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "SLCO1B3",
      "name": "SLCO1B3",
      "type": "protein",
      "degree": 3
    },
    {
      "id": "SLC31A2",
      "name": "SLC31A2",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "ATP7B",
      "name": "ATP7B",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "ATP7A",
      "name": "ATP7A",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "SLC47A2",
      "name": "SLC47A2",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "RALBP1",
      "name": "RALBP1",
      "type": "protein",
      "degree": 1
    },
    {
      "id": "hypertensive disorder",
      "name": "hypertensive disorder",
      "type": "disease",
      "degree": 1
    },
    {
      "id": "hypertension",
      "name": "hypertension",
      "type": "disease",
      "degree": 1
    },
    {
      "id": "Temozolomide",
      "name": "Temozolomide",
      "type": "drug",
      "degree": 1
    },
    {
      "id": "liver failure",
      "name": "liver failure",
      "type": "disease",
      "degree": 2
    },
    {
      "id": "anxiety disorder",
      "name": "anxiety disorder",
      "type": "disease",
      "degree": 1
    },
    {
      "id": "neurotic disorder",
      "name": "neurotic disorder",
      "type": "disease",
      "degree": 1
    }
  ],
  "edges": [
    {
      "id": "e_0",
      "source": "Cisplatin",
      "target": "ALB",
      "relation": "carrier"
    },
    {
      "id": "e_1",
      "source": "Irinotecan",
      "target": "ALB",
      "relation": "carrier"
    },
    {
      "id": "e_2",
      "source": "Cisplatin",
      "target": "PTGS2",
      "relation": "enzyme"
    },
    {
      "id": "e_3",
      "source": "Cisplatin",
      "target": "CYP4A11",
      "relation": "enzyme"
    },
    {
      "id": "e_4",
      "source": "Cisplatin",
      "target": "GSTM1",
      "relation": "enzyme"
    },
    {
      "id": "e_5",
      "source": "Cisplatin",
      "target": "GSTP1",
      "relation": "enzyme"
    },
    {
      "id": "e_6",
      "source": "Cisplatin",
      "target": "GSTT1",
      "relation": "enzyme"
    },
    {
      "id": "e_7",
      "source": "Cisplatin",
      "target": "MPO",
      "relation": "enzyme"
    },
    {
      "id": "e_8",
      "source": "Paclitaxel",
      "target": "CYP1B1",
      "relation": "enzyme"
    },
    {
      "id": "e_9",
      "source": "Docetaxel",
      "target": "CYP1B1",
      "relation": "enzyme"
    },
    {
      "id": "e_10",
      "source": "Cisplatin",
      "target": "NQO1",
      "relation": "enzyme"
    },
    {
      "id": "e_11",
      "source": "Paclitaxel",
      "target": "CYP19A1",
      "relation": "enzyme"
    },
    {
      "id": "e_12",
      "source": "Cisplatin",
      "target": "BCHE",
      "relation": "enzyme"
    },
    {
      "id": "e_13",
      "source": "Irinotecan",
      "target": "BCHE",
      "relation": "enzyme"
    },
    {
      "id": "e_14",
      "source": "Cisplatin",
      "target": "XDH",
      "relation": "enzyme"
    },
    {
      "id": "e_15",
      "source": "Cyclophosphamide",
      "target": "CYP3A5",
      "relation": "enzyme"
    },
    {
      "id": "e_16",
      "source": "Vincristine",
      "target": "CYP3A5",
      "relation": "enzyme"
    },
    {
      "id": "e_17",
      "source": "Irinotecan",
      "target": "CYP3A5",
      "relation": "enzyme"
    },
    {
      "id": "e_18",
      "source": "Paclitaxel",
      "target": "CYP3A5",
      "relation": "enzyme"
    },
    {
      "id": "e_19",
      "source": "Docetaxel",
      "target": "CYP3A5",
      "relation": "enzyme"
    },
    {
      "id": "e_20",
      "source": "Cisplatin",
      "target": "SOD1",
      "relation": "enzyme"
    },
    {
      "id": "e_21",
      "source": "Cyclophosphamide",
      "target": "CYP3A4",
      "relation": "enzyme"
    },
    {
      "id": "e_22",
      "source": "Vincristine",
      "target": "CYP3A4",
      "relation": "enzyme"
    },
    {
      "id": "e_23",
      "source": "Irinotecan",
      "target": "CYP3A4",
      "relation": "enzyme"
    },
    {
      "id": "e_24",
      "source": "Topotecan",
      "target": "CYP3A4",
      "relation": "enzyme"
    },
    {
      "id": "e_25",
      "source": "Paclitaxel",
      "target": "CYP3A4",
      "relation": "enzyme"
    },
    {
      "id": "e_26",
      "source": "Docetaxel",
      "target": "CYP3A4",
      "relation": "enzyme"
    },
    {
      "id": "e_27",
      "source": "Irinotecan",
      "target": "CES1",
      "relation": "enzyme"
    },
    {
      "id": "e_28",
      "source": "Cisplatin",
      "target": "CYP2C9",
      "relation": "enzyme"
    },
    {
      "id": "e_29",
      "source": "Cyclophosphamide",
      "target": "CYP2C9",
      "relation": "enzyme"
    },
    {
      "id": "e_30",
      "source": "Cyclophosphamide",
      "target": "CYP2C8",
      "relation": "enzyme"
    },
    {
      "id": "e_31",
      "source": "Paclitaxel",
      "target": "CYP2C8",
      "relation": "enzyme"
    },
    {
      "id": "e_32",
      "source": "Cyclophosphamide",
      "target": "CYP2A6",
      "relation": "enzyme"
    },
    {
      "id": "e_33",
      "source": "Cyclophosphamide",
      "target": "CYP2C19",
      "relation": "enzyme"
    },
    {
      "id": "e_34",
      "source": "Irinotecan",
      "target": "UGT1A9",
      "relation": "enzyme"
    },
    {
      "id": "e_35",
      "source": "Irinotecan",
      "target": "UGT1A1",
      "relation": "enzyme"
    },
    {
      "id": "e_36",
      "source": "Cisplatin",
      "target": "CYP2B6",
      "relation": "enzyme"
    },
    {
      "id": "e_37",
      "source": "Cyclophosphamide",
      "target": "CYP2B6",
      "relation": "enzyme"
    },
    {
      "id": "e_38",
      "source": "Irinotecan",
      "target": "CYP2B6",
      "relation": "enzyme"
    },
    {
      "id": "e_39",
      "source": "Cyclophosphamide",
      "target": "CYP2C18",
      "relation": "enzyme"
    },
    {
      "id": "e_40",
      "source": "Vincristine",
      "target": "CYP3A7",
      "relation": "enzyme"
    },
    {
      "id": "e_41",
      "source": "Irinotecan",
      "target": "CYP3A7",
      "relation": "enzyme"
    },
    {
      "id": "e_42",
      "source": "Paclitaxel",
      "target": "CYP3A7",
      "relation": "enzyme"
    },
    {
      "id": "e_43",
      "source": "Docetaxel",
      "target": "CYP3A7",
      "relation": "enzyme"
    },
    {
      "id": "e_44",
      "source": "Irinotecan",
      "target": "CES2",
      "relation": "enzyme"
    },
    {
      "id": "e_45",
      "source": "Cisplatin",
      "target": "MT1A",
      "relation": "enzyme"
    },
    {
      "id": "e_46",
      "source": "Cisplatin",
      "target": "MT2A",
      "relation": "enzyme"
    },
    {
      "id": "e_47",
      "source": "Paclitaxel",
      "target": "TUBB1",
      "relation": "target"
    },
    {
      "id": "e_48",
      "source": "Docetaxel",
      "target": "TUBB1",
      "relation": "target"
    },
    {
      "id": "e_49",
      "source": "Irinotecan",
      "target": "TOP1MT",
      "relation": "target"
    },
    {
      "id": "e_50",
      "source": "Topotecan",
      "target": "TOP1MT",
      "relation": "target"
    },
    {
      "id": "e_51",
      "source": "Vincristine",
      "target": "TUBB",
      "relation": "target"
    },
    {
      "id": "e_52",
      "source": "Paclitaxel",
      "target": "BCL2",
      "relation": "target"
    },
    {
      "id": "e_53",
      "source": "Docetaxel",
      "target": "BCL2",
      "relation": "target"
    },
    {
      "id": "e_54",
      "source": "Cisplatin",
      "target": "TF",
      "relation": "target"
    },
    {
      "id": "e_55",
      "source": "Cisplatin",
      "target": "A2M",
      "relation": "target"
    },
    {
      "id": "e_56",
      "source": "Cyclophosphamide",
      "target": "NR1I2",
      "relation": "target"
    },
    {
      "id": "e_57",
      "source": "Paclitaxel",
      "target": "NR1I2",
      "relation": "target"
    },
    {
      "id": "e_58",
      "source": "Docetaxel",
      "target": "NR1I2",
      "relation": "target"
    },
    {
      "id": "e_59",
      "source": "Irinotecan",
      "target": "TOP1",
      "relation": "target"
    },
    {
      "id": "e_60",
      "source": "Topotecan",
      "target": "TOP1",
      "relation": "target"
    },
    {
      "id": "e_61",
      "source": "Paclitaxel",
      "target": "MAP2",
      "relation": "target"
    },
    {
      "id": "e_62",
      "source": "Docetaxel",
      "target": "MAP2",
      "relation": "target"
    },
    {
      "id": "e_63",
      "source": "Vincristine",
      "target": "TUBA4A",
      "relation": "target"
    },
    {
      "id": "e_64",
      "source": "Cisplatin",
      "target": "ATOX1",
      "relation": "target"
    },
    {
      "id": "e_65",
      "source": "Paclitaxel",
      "target": "MAPT",
      "relation": "target"
    },
    {
      "id": "e_66",
      "source": "Docetaxel",
      "target": "MAPT",
      "relation": "target"
    },
    {
      "id": "e_67",
      "source": "Paclitaxel",
      "target": "MAP4",
      "relation": "target"
    },
    {
      "id": "e_68",
      "source": "Docetaxel",
      "target": "MAP4",
      "relation": "target"
    },
    {
      "id": "e_69",
      "source": "Cisplatin",
      "target": "MPG",
      "relation": "target"
    },
    {
      "id": "e_70",
      "source": "Vincristine",
      "target": "ABCB11",
      "relation": "transporter"
    },
    {
      "id": "e_71",
      "source": "Paclitaxel",
      "target": "ABCB11",
      "relation": "transporter"
    },
    {
      "id": "e_72",
      "source": "Vincristine",
      "target": "ABCC1",
      "relation": "transporter"
    },
    {
      "id": "e_73",
      "source": "Irinotecan",
      "target": "ABCC1",
      "relation": "transporter"
    },
    {
      "id": "e_74",
      "source": "Paclitaxel",
      "target": "ABCC1",
      "relation": "transporter"
    },
    {
      "id": "e_75",
      "source": "Docetaxel",
      "target": "ABCC1",
      "relation": "transporter"
    },
    {
      "id": "e_76",
      "source": "Vincristine",
      "target": "SLCO1B1",
      "relation": "transporter"
    },
    {
      "id": "e_77",
      "source": "Irinotecan",
      "target": "SLCO1B1",
      "relation": "transporter"
    },
    {
      "id": "e_78",
      "source": "Vincristine",
      "target": "ABCB1",
      "relation": "transporter"
    },
    {
      "id": "e_79",
      "source": "Irinotecan",
      "target": "ABCB1",
      "relation": "transporter"
    },
    {
      "id": "e_80",
      "source": "Topotecan",
      "target": "ABCB1",
      "relation": "transporter"
    },
    {
      "id": "e_81",
      "source": "Paclitaxel",
      "target": "ABCB1",
      "relation": "transporter"
    },
    {
      "id": "e_82",
      "source": "Docetaxel",
      "target": "ABCB1",
      "relation": "transporter"
    },
    {
      "id": "e_83",
      "source": "Cisplatin",
      "target": "ABCC3",
      "relation": "transporter"
    },
    {
      "id": "e_84",
      "source": "Vincristine",
      "target": "ABCC3",
      "relation": "transporter"
    },
    {
      "id": "e_85",
      "source": "Cisplatin",
      "target": "ABCG2",
      "relation": "transporter"
    },
    {
      "id": "e_86",
      "source": "Vincristine",
      "target": "ABCG2",
      "relation": "transporter"
    },
    {
      "id": "e_87",
      "source": "Irinotecan",
      "target": "ABCG2",
      "relation": "transporter"
    },
    {
      "id": "e_88",
      "source": "Topotecan",
      "target": "ABCG2",
      "relation": "transporter"
    },
    {
      "id": "e_89",
      "source": "Docetaxel",
      "target": "ABCG2",
      "relation": "transporter"
    },
    {
      "id": "e_90",
      "source": "Cisplatin",
      "target": "ABCC2",
      "relation": "transporter"
    },
    {
      "id": "e_91",
      "source": "Vincristine",
      "target": "ABCC2",
      "relation": "transporter"
    },
    {
      "id": "e_92",
      "source": "Irinotecan",
      "target": "ABCC2",
      "relation": "transporter"
    },
    {
      "id": "e_93",
      "source": "Paclitaxel",
      "target": "ABCC2",
      "relation": "transporter"
    },
    {
      "id": "e_94",
      "source": "Docetaxel",
      "target": "ABCC2",
      "relation": "transporter"
    },
    {
      "id": "e_95",
      "source": "Cisplatin",
      "target": "ABCC5",
      "relation": "transporter"
    },
    {
      "id": "e_96",
      "source": "Cisplatin",
      "target": "ABCC6",
      "relation": "transporter"
    },
    {
      "id": "e_97",
      "source": "Docetaxel",
      "target": "SLC22A7",
      "relation": "transporter"
    },
    {
      "id": "e_98",
      "source": "Cisplatin",
      "target": "SLC22A2",
      "relation": "transporter"
    },
    {
      "id": "e_99",
      "source": "Cisplatin",
      "target": "SLC31A1",
      "relation": "transporter"
    },
    {
      "id": "e_100",
      "source": "Vincristine",
      "target": "SLC22A3",
      "relation": "transporter"
    },
    {
      "id": "e_101",
      "source": "Irinotecan",
      "target": "SLC22A3",
      "relation": "transporter"
    },
    {
      "id": "e_102",
      "source": "Vincristine",
      "target": "ABCC10",
      "relation": "transporter"
    },
    {
      "id": "e_103",
      "source": "Paclitaxel",
      "target": "ABCC10",
      "relation": "transporter"
    },
    {
      "id": "e_104",
      "source": "Docetaxel",
      "target": "ABCC10",
      "relation": "transporter"
    },
    {
      "id": "e_105",
      "source": "Topotecan",
      "target": "SLC47A1",
      "relation": "transporter"
    },
    {
      "id": "e_106",
      "source": "Vincristine",
      "target": "SLCO1B3",
      "relation": "transporter"
    },
    {
      "id": "e_107",
      "source": "Paclitaxel",
      "target": "SLCO1B3",
      "relation": "transporter"
    },
    {
      "id": "e_108",
      "source": "Docetaxel",
      "target": "SLCO1B3",
      "relation": "transporter"
    },
    {
      "id": "e_109",
      "source": "Cisplatin",
      "target": "SLC31A2",
      "relation": "transporter"
    },
    {
      "id": "e_110",
      "source": "Cisplatin",
      "target": "ATP7B",
      "relation": "transporter"
    },
    {
      "id": "e_111",
      "source": "Cisplatin",
      "target": "ATP7A",
      "relation": "transporter"
    },
    {
      "id": "e_112",
      "source": "Topotecan",
      "target": "SLC47A2",
      "relation": "transporter"
    },
    {
      "id": "e_113",
      "source": "Vincristine",
      "target": "RALBP1",
      "relation": "transporter"
    },
    {
      "id": "e_114",
      "source": "Paclitaxel",
      "target": "hypertensive disorder",
      "relation": "indication"
    },
    {
      "id": "e_115",
      "source": "Paclitaxel",
      "target": "hypertension",
      "relation": "indication"
    },
    {
      "id": "e_116",
      "source": "Temozolomide",
      "target": "liver failure",
      "relation": "contraindication"
    },
    {
      "id": "e_117",
      "source": "Vincristine",
      "target": "liver failure",
      "relation": "contraindication"
    },
    {
      "id": "e_118",
      "source": "Paclitaxel",
      "target": "anxiety disorder",
      "relation": "contraindication"
    },
    {
      "id": "e_119",
      "source": "Paclitaxel",
      "target": "neurotic disorder",
      "relation": "contraindication"
    }
  ]
};
