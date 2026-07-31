### O
Not part of any labeled span; default/background label.

### B-Production
First token of a **Production** event span. Dynamic event that indicates the production of a commodity

### I-Production
Non-initial (continuation) token of a **Production** event span, i.e. a token that continues an event of type Production begun by a preceding B-Production or I-Production token. Dynamic event that indicates the production of a commodity

### B-Mismanagement
First token of a **Mismanagement** event span. Dynamic event that indicates that a region is being mismanaged.

### I-Mismanagement
Non-initial (continuation) token of a **Mismanagement** event span, i.e. a token that continues an event of type Mismanagement begun by a preceding B-Mismanagement or I-Mismanagement token. Dynamic event that indicates that a region is being mismanaged.

### B-SocialInteraction
First token of a **SocialInteraction** event span. Dynamic event where people interact. This is a high-level umbrella event, which means it is generally too broad to annotate with. When you want to annotate events that indicate a communicative interaction of some sort, use Communication.

### I-SocialInteraction
Non-initial (continuation) token of a **SocialInteraction** event span, i.e. a token that continues an event of type SocialInteraction begun by a preceding B-SocialInteraction or I-SocialInteraction token. Dynamic event where people interact. This is a high-level umbrella event, which means it is generally too broad to annotate with. When you want to annotate events that indicate a communicative interaction of some sort, use Communication.

### B-Communication
First token of a **Communication** event span. Dynamic event that indicates a communicative interaction between two people, organisations or groups of people. Examples of communication events are giving orders, replying to letters, confessions, conversations.

### I-Communication
Non-initial (continuation) token of a **Communication** event span, i.e. a token that continues an event of type Communication begun by a preceding B-Communication or I-Communication token. Dynamic event that indicates a communicative interaction between two people, organisations or groups of people. Examples of communication events are giving orders, replying to letters, confessions, conversations.

### B-Request
First token of a **Request** event span. The subclass of SocialInteraction where a person or organization requests something.

### I-Request
Non-initial (continuation) token of a **Request** event span, i.e. a token that continues an event of type Request begun by a preceding B-Request or I-Request token. The subclass of SocialInteraction where a person or organization requests something.

### B-ForceToAct
First token of a **ForceToAct** event span. The subclass of SocialInteraction where a person or organization forces a second party to act in some way, do or not do something. Giving orders through written communication does not fall under ForceToAct. Forcing to act goes beyond having a duty to do something: there is a known or implied consequence involved.

### I-ForceToAct
Non-initial (continuation) token of a **ForceToAct** event span, i.e. a token that continues an event of type ForceToAct begun by a preceding B-ForceToAct or I-ForceToAct token. The subclass of SocialInteraction where a person or organization forces a second party to act in some way, do or not do something. Giving orders through written communication does not fall under ForceToAct. Forcing to act goes beyond having a duty to do something: there is a known or implied consequence involved.

### B-Encounter
First token of a **Encounter** event span. The subclass of SocialInteraction where people, organizations or ships meet each other, either planned or unplanned.

### I-Encounter
Non-initial (continuation) token of a **Encounter** event span, i.e. a token that continues an event of type Encounter begun by a preceding B-Encounter or I-Encounter token. The subclass of SocialInteraction where people, organizations or ships meet each other, either planned or unplanned.

### B-Visit
First token of a **Visit** event span. The subclass of SocialInteraction where a person or organization goes to visit another person or organization. This event includes diplomatic and non-diplomatic visits.

### I-Visit
Non-initial (continuation) token of a **Visit** event span, i.e. a token that continues an event of type Visit begun by a preceding B-Visit or I-Visit token. The subclass of SocialInteraction where a person or organization goes to visit another person or organization. This event includes diplomatic and non-diplomatic visits.

### B-ViolentContest
First token of a **ViolentContest** event span. The subclass of SocialInteraction where two parties interact in a hostile manner using violence.

### I-ViolentContest
Non-initial (continuation) token of a **ViolentContest** event span, i.e. a token that continues an event of type ViolentContest begun by a preceding B-ViolentContest or I-ViolentContest token. The subclass of SocialInteraction where two parties interact in a hostile manner using violence.

### B-Attacking
First token of a **Attacking** event span. The subclass of ViolentContest where someone or something is assaulted with the intention to cause some harm.

### I-Attacking
Non-initial (continuation) token of a **Attacking** event span, i.e. a token that continues an event of type Attacking begun by a preceding B-Attacking or I-Attacking token. The subclass of ViolentContest where someone or something is assaulted with the intention to cause some harm.

### B-SocialStatusChange
First token of a **SocialStatusChange** event span. Dynamic event where the social status of a person or organization is altered in some way.

### I-SocialStatusChange
Non-initial (continuation) token of a **SocialStatusChange** event span, i.e. a token that continues an event of type SocialStatusChange begun by a preceding B-SocialStatusChange or I-SocialStatusChange token. Dynamic event where the social status of a person or organization is altered in some way.

### B-RelationshipChange
First token of a **RelationshipChange** event span. A subclass of SocialStatusChange. Different from AlteringARelationship, the change can include the beginning or the end of a relationship.

### I-RelationshipChange
Non-initial (continuation) token of a **RelationshipChange** event span, i.e. a token that continues an event of type RelationshipChange begun by a preceding B-RelationshipChange or I-RelationshipChange token. A subclass of SocialStatusChange. Different from AlteringARelationship, the change can include the beginning or the end of a relationship.

### B-InternalChange
First token of a **InternalChange** event span. DynamicEvent where some internal quality of a person or entity changes.

### I-InternalChange
Non-initial (continuation) token of a **InternalChange** event span, i.e. a token that continues an event of type InternalChange begun by a preceding B-InternalChange or I-InternalChange token. DynamicEvent where some internal quality of a person or entity changes.

### B-ScalarChange
First token of a **ScalarChange** event span. The subclass of InternalChange where something changes position on a scale.

### I-ScalarChange
Non-initial (continuation) token of a **ScalarChange** event span, i.e. a token that continues an event of type ScalarChange begun by a preceding B-ScalarChange or I-ScalarChange token. The subclass of InternalChange where something changes position on a scale.

### B-QuantityChange
First token of a **QuantityChange** event span. The subclass of ScalarChange where some quantity is altered.

### I-QuantityChange
Non-initial (continuation) token of a **QuantityChange** event span, i.e. a token that continues an event of type QuantityChange begun by a preceding B-QuantityChange or I-QuantityChange token. The subclass of ScalarChange where some quantity is altered.

### B-Increasing
First token of a **Increasing** event span. The subclass of QuantityChange where some physical quantity or value is increased

### I-Increasing
Non-initial (continuation) token of a **Increasing** event span, i.e. a token that continues an event of type Increasing begun by a preceding B-Increasing or I-Increasing token. The subclass of QuantityChange where some physical quantity or value is increased

### B-Decreasing
First token of a **Decreasing** event span. The subclass of QuantityChange where some physical quantity or value is decreased.

### I-Decreasing
Non-initial (continuation) token of a **Decreasing** event span, i.e. a token that continues an event of type Decreasing begun by a preceding B-Decreasing or I-Decreasing token. The subclass of QuantityChange where some physical quantity or value is decreased.

### B-BeingInDebt
First token of a **BeingInDebt** event span. DynamicEvent where a person or organization has a debt patient = The person / organization / entity that has a debt

### I-BeingInDebt
Non-initial (continuation) token of a **BeingInDebt** event span, i.e. a token that continues an event of type BeingInDebt begun by a preceding B-BeingInDebt or I-BeingInDebt token. DynamicEvent where a person or organization has a debt patient = The person / organization / entity that has a debt

### B-BeingAtPeace
First token of a **BeingAtPeace** event span. DynamicEvent where two parties are explicitly at peace. patient = The person(s) / organization(s) that are at peace

### I-BeingAtPeace
Non-initial (continuation) token of a **BeingAtPeace** event span, i.e. a token that continues an event of type BeingAtPeace begun by a preceding B-BeingAtPeace or I-BeingAtPeace token. DynamicEvent where two parties are explicitly at peace. patient = The person(s) / organization(s) that are at peace

### B-BeingAtAPlace
First token of a **BeingAtAPlace** event span. Static Event where some entity is at a location.

### I-BeingAtAPlace
Non-initial (continuation) token of a **BeingAtAPlace** event span, i.e. a token that continues an event of type BeingAtAPlace begun by a preceding B-BeingAtAPlace or I-BeingAtAPlace token. Static Event where some entity is at a location.

### B-Translocation
First token of a **Translocation** event span. DynamicEvent where physical objects or animate beings change from location.

### I-Translocation
Non-initial (continuation) token of a **Translocation** event span, i.e. a token that continues an event of type Translocation begun by a preceding B-Translocation or I-Translocation token. DynamicEvent where physical objects or animate beings change from location.

### B-Leaving
First token of a **Leaving** event span. The subclass of Translocation where someone or something leaves a location.

### I-Leaving
Non-initial (continuation) token of a **Leaving** event span, i.e. a token that continues an event of type Leaving begun by a preceding B-Leaving or I-Leaving token. The subclass of Translocation where someone or something leaves a location.

### B-Arriving
First token of a **Arriving** event span. The subclass of Translocation where someone or something arrives at a location.

### I-Arriving
Non-initial (continuation) token of a **Arriving** event span, i.e. a token that continues an event of type Arriving begun by a preceding B-Arriving or I-Arriving token. The subclass of Translocation where someone or something arrives at a location.

### B-Voyage
First token of a **Voyage** event span. The subclass of Translocation where a ship or group of ships travels for a longer period of time.

### I-Voyage
Non-initial (continuation) token of a **Voyage** event span, i.e. a token that continues an event of type Voyage begun by a preceding B-Voyage or I-Voyage token. The subclass of Translocation where a ship or group of ships travels for a longer period of time.

### B-Transportation
First token of a **Transportation** event span. The subclass of Translocation where physical objects and animate beings together change from location and the physical object is not the means of translocation.

### I-Transportation
Non-initial (continuation) token of a **Transportation** event span, i.e. a token that continues an event of type Transportation begun by a preceding B-Transportation or I-Transportation token. The subclass of Translocation where physical objects and animate beings together change from location and the physical object is not the means of translocation.

### B-HavingInPossession
First token of a **HavingInPossession** event span. Property where someone holds on to someone or something for a period of time.

### I-HavingInPossession
Non-initial (continuation) token of a **HavingInPossession** event span, i.e. a token that continues an event of type HavingInPossession begun by a preceding B-HavingInPossession or I-HavingInPossession token. Property where someone holds on to someone or something for a period of time.

### B-ChangeOfPossession
First token of a **ChangeOfPossession** event span. DynamicEvent where some entity changes possession. Note that this often but not necessarily implies a change of location of the entity.

### I-ChangeOfPossession
Non-initial (continuation) token of a **ChangeOfPossession** event span, i.e. a token that continues an event of type ChangeOfPossession begun by a preceding B-ChangeOfPossession or I-ChangeOfPossession token. DynamicEvent where some entity changes possession. Note that this often but not necessarily implies a change of location of the entity.

### B-Getting
First token of a **Getting** event span. The subclass of ChangeOfPossession where a person gets or receives some item.

### I-Getting
Non-initial (continuation) token of a **Getting** event span, i.e. a token that continues an event of type Getting begun by a preceding B-Getting or I-Getting token. The subclass of ChangeOfPossession where a person gets or receives some item.

### B-LosingPossession
First token of a **LosingPossession** event span. The subclass of ChangeOfPossession where a person or organization loses possession of something.

### I-LosingPossession
Non-initial (continuation) token of a **LosingPossession** event span, i.e. a token that continues an event of type LosingPossession begun by a preceding B-LosingPossession or I-LosingPossession token. The subclass of ChangeOfPossession where a person or organization loses possession of something.

### B-Giving
First token of a **Giving** event span. The subclass of ChangeOfPossession where a person gives something to someone else.

### I-Giving
Non-initial (continuation) token of a **Giving** event span, i.e. a token that continues an event of type Giving begun by a preceding B-Giving or I-Giving token. The subclass of ChangeOfPossession where a person gives something to someone else.

### B-Trade
First token of a **Trade** event span. The subclass of ChangeOfPossession where some item changes of ownership in exchange for money or other goods.

### I-Trade
Non-initial (continuation) token of a **Trade** event span, i.e. a token that continues an event of type Trade begun by a preceding B-Trade or I-Trade token. The subclass of ChangeOfPossession where some item changes of ownership in exchange for money or other goods.

### B-FinancialTransaction
First token of a **FinancialTransaction** event span. The subclass of ChangeOfPossession where a monetary value changes ownership.

### I-FinancialTransaction
Non-initial (continuation) token of a **FinancialTransaction** event span, i.e. a token that continues an event of type FinancialTransaction begun by a preceding B-FinancialTransaction or I-FinancialTransaction token. The subclass of ChangeOfPossession where a monetary value changes ownership.

### B-Buying
First token of a **Buying** event span. The subclass of Trade where some entity changes of ownership in exchange for another entity or money.

### I-Buying
Non-initial (continuation) token of a **Buying** event span, i.e. a token that continues an event of type Buying begun by a preceding B-Buying or I-Buying token. The subclass of Trade where some entity changes of ownership in exchange for another entity or money.

### B-Selling
First token of a **Selling** event span. The subclass of Trade where some entity changes of ownership in exchange for another entity or money.

### I-Selling
Non-initial (continuation) token of a **Selling** event span, i.e. a token that continues an event of type Selling begun by a preceding B-Selling or I-Selling token. The subclass of Trade where some entity changes of ownership in exchange for another entity or money.

### B-BeingInARelationship
First token of a **BeingInARelationship** event span. Property where persons or organizations are in some relationship.

### I-BeingInARelationship
Non-initial (continuation) token of a **BeingInARelationship** event span, i.e. a token that continues an event of type BeingInARelationship begun by a preceding B-BeingInARelationship or I-BeingInARelationship token. Property where persons or organizations are in some relationship.

### B-BeginningARelationship
First token of a **BeginningARelationship** event span. The subclass of SocialStatusChange where people or organizations start or form a relationship with each other

### I-BeginningARelationship
Non-initial (continuation) token of a **BeginningARelationship** event span, i.e. a token that continues an event of type BeginningARelationship begun by a preceding B-BeginningARelationship or I-BeginningARelationship token. The subclass of SocialStatusChange where people or organizations start or form a relationship with each other

### B-EndingARelationship
First token of a **EndingARelationship** event span. The subclass of SocialStatusChange where people or organizations end a relationship with each other.

### I-EndingARelationship
Non-initial (continuation) token of a **EndingARelationship** event span, i.e. a token that continues an event of type EndingARelationship begun by a preceding B-EndingARelationship or I-EndingARelationship token. The subclass of SocialStatusChange where people or organizations end a relationship with each other.

### B-AlteringARelationship
First token of a **AlteringARelationship** event span. The subclass of SocialStatusChange where the status or nature of a relationship is altered. This class assumes an existing relationship both before and after the event of altering.

### I-AlteringARelationship
Non-initial (continuation) token of a **AlteringARelationship** event span, i.e. a token that continues an event of type AlteringARelationship begun by a preceding B-AlteringARelationship or I-AlteringARelationship token. The subclass of SocialStatusChange where the status or nature of a relationship is altered. This class assumes an existing relationship both before and after the event of altering.

### B-BeingLeader
First token of a **BeingLeader** event span. Property where someone is leader of some group of persons or organization

### I-BeingLeader
Non-initial (continuation) token of a **BeingLeader** event span, i.e. a token that continues an event of type BeingLeader begun by a preceding B-BeingLeader or I-BeingLeader token. Property where someone is leader of some group of persons or organization

### B-Replacing
First token of a **Replacing** event span. The subclass of SocialStatusChange where someone or something is replaced with someone or something else in a specific role or function.

### I-Replacing
Non-initial (continuation) token of a **Replacing** event span, i.e. a token that continues an event of type Replacing begun by a preceding B-Replacing or I-Replacing token. The subclass of SocialStatusChange where someone or something is replaced with someone or something else in a specific role or function.

### B-Election
First token of a **Election** event span. The subclass of SocialStatusChange where someone is elected to be in a specific role or function.

### I-Election
Non-initial (continuation) token of a **Election** event span, i.e. a token that continues an event of type Election begun by a preceding B-Election or I-Election token. The subclass of SocialStatusChange where someone is elected to be in a specific role or function.

### B-BeingEmployed
First token of a **BeingEmployed** event span. Property where someone is working in a position and is compensated for her work by some form of payment.

### I-BeingEmployed
Non-initial (continuation) token of a **BeingEmployed** event span, i.e. a token that continues an event of type BeingEmployed begun by a preceding B-BeingEmployed or I-BeingEmployed token. Property where someone is working in a position and is compensated for her work by some form of payment.

### B-JoiningAnOrganization
First token of a **JoiningAnOrganization** event span. The subclass of SocialStatusChange where someone starts working as an employee for some organization.

### I-JoiningAnOrganization
Non-initial (continuation) token of a **JoiningAnOrganization** event span, i.e. a token that continues an event of type JoiningAnOrganization begun by a preceding B-JoiningAnOrganization or I-JoiningAnOrganization token. The subclass of SocialStatusChange where someone starts working as an employee for some organization.

### B-LeavingAnOrganization
First token of a **LeavingAnOrganization** event span. The subclass of SocialStatusChange where a person stops working as an employee for an organization.

### I-LeavingAnOrganization
Non-initial (continuation) token of a **LeavingAnOrganization** event span, i.e. a token that continues an event of type LeavingAnOrganization begun by a preceding B-LeavingAnOrganization or I-LeavingAnOrganization token. The subclass of SocialStatusChange where a person stops working as an employee for an organization.

### B-HavingContractualAgreement
First token of a **HavingContractualAgreement** event span. Static event where two polities have a contractual agreement.

### I-HavingContractualAgreement
Non-initial (continuation) token of a **HavingContractualAgreement** event span, i.e. a token that continues an event of type HavingContractualAgreement begun by a preceding B-HavingContractualAgreement or I-HavingContractualAgreement token. Static event where two polities have a contractual agreement.

### B-Collaboration
First token of a **Collaboration** event span. Static event where two people, polities or organisations are in some way collaborating (not always voluntarily).

### I-Collaboration
Non-initial (continuation) token of a **Collaboration** event span, i.e. a token that continues an event of type Collaboration begun by a preceding B-Collaboration or I-Collaboration token. Static event where two people, polities or organisations are in some way collaborating (not always voluntarily).

### B-BeginningContractualAgreement
First token of a **BeginningContractualAgreement** event span. The subclass of SocialStatusChange where two parties enter in an agreement described in a contract.

### I-BeginningContractualAgreement
Non-initial (continuation) token of a **BeginningContractualAgreement** event span, i.e. a token that continues an event of type BeginningContractualAgreement begun by a preceding B-BeginningContractualAgreement or I-BeginningContractualAgreement token. The subclass of SocialStatusChange where two parties enter in an agreement described in a contract.

### B-EndingContractualAgreement
First token of a **EndingContractualAgreement** event span. The subclass of SocialStatusChange where a contract between two parties is broken by one or both of the parties involved, either by illegally breaking the contract or ending it together.

### I-EndingContractualAgreement
Non-initial (continuation) token of a **EndingContractualAgreement** event span, i.e. a token that continues an event of type EndingContractualAgreement begun by a preceding B-EndingContractualAgreement or I-EndingContractualAgreement token. The subclass of SocialStatusChange where a contract between two parties is broken by one or both of the parties involved, either by illegally breaking the contract or ending it together.

### B-ExtendingContractualAgreement
First token of a **ExtendingContractualAgreement** event span. The subclass of SocialStatusChange where a contract between two parties is extended by one or both of the parties involved.

### I-ExtendingContractualAgreement
Non-initial (continuation) token of a **ExtendingContractualAgreement** event span, i.e. a token that continues an event of type ExtendingContractualAgreement begun by a preceding B-ExtendingContractualAgreement or I-ExtendingContractualAgreement token. The subclass of SocialStatusChange where a contract between two parties is extended by one or both of the parties involved.

### B-Unrest
First token of a **Unrest** event span. The subclass of StaticEvent where there is unrest within an organization or polity.

### I-Unrest
Non-initial (continuation) token of a **Unrest** event span, i.e. a token that continues an event of type Unrest begun by a preceding B-Unrest or I-Unrest token. The subclass of StaticEvent where there is unrest within an organization or polity.

### B-Uprising
First token of a **Uprising** event span. The subclass of ViolentContest where humans rise against some authority.

### I-Uprising
Non-initial (continuation) token of a **Uprising** event span, i.e. a token that continues an event of type Uprising begun by a preceding B-Uprising or I-Uprising token. The subclass of ViolentContest where humans rise against some authority.

### B-Riot
First token of a **Riot** event span. The subclass of Uprising where some group of people engage in a violent disturbance of the public order.

### I-Riot
Non-initial (continuation) token of a **Riot** event span, i.e. a token that continues an event of type Riot begun by a preceding B-Riot or I-Riot token. The subclass of Uprising where some group of people engage in a violent disturbance of the public order.

### B-Mutiny
First token of a **Mutiny** event span. The subclass of Uprising where a group of people rise against some authority, especially used for rebellion at ships or in armies.

### I-Mutiny
Non-initial (continuation) token of a **Mutiny** event span, i.e. a token that continues an event of type Mutiny begun by a preceding B-Mutiny or I-Mutiny token. The subclass of Uprising where a group of people rise against some authority, especially used for rebellion at ships or in armies.

### B-PoliticalRevolution
First token of a **PoliticalRevolution** event span. The subclass of Uprising where some government is violently overthrown and replaced by another government.

### I-PoliticalRevolution
Non-initial (continuation) token of a **PoliticalRevolution** event span, i.e. a token that continues an event of type PoliticalRevolution begun by a preceding B-PoliticalRevolution or I-PoliticalRevolution token. The subclass of Uprising where some government is violently overthrown and replaced by another government.

### B-BeingInConflict
First token of a **BeingInConflict** event span. Property where two people or groups of people are in conflict with each other.

### I-BeingInConflict
Non-initial (continuation) token of a **BeingInConflict** event span, i.e. a token that continues an event of type BeingInConflict begun by a preceding B-BeingInConflict or I-BeingInConflict token. Property where two people or groups of people are in conflict with each other.

### B-StartingConflict
First token of a **StartingConflict** event span. The subclass of SocialInteraction where a conflict is being started.

### I-StartingConflict
Non-initial (continuation) token of a **StartingConflict** event span, i.e. a token that continues an event of type StartingConflict begun by a preceding B-StartingConflict or I-StartingConflict token. The subclass of SocialInteraction where a conflict is being started.

### B-EndingConflict
First token of a **EndingConflict** event span. The subclass of SocialInteraction where a conflict is made to come to an end.

### I-EndingConflict
Non-initial (continuation) token of a **EndingConflict** event span, i.e. a token that continues an event of type EndingConflict begun by a preceding B-EndingConflict or I-EndingConflict token. The subclass of SocialInteraction where a conflict is made to come to an end.

### B-StartingAWar
First token of a **StartingAWar** event span. The subclass of StartingConflict where an armed conflict between different groups of people, two or more countries, etc. is being started.

### I-StartingAWar
Non-initial (continuation) token of a **StartingAWar** event span, i.e. a token that continues an event of type StartingAWar begun by a preceding B-StartingAWar or I-StartingAWar token. The subclass of StartingConflict where an armed conflict between different groups of people, two or more countries, etc. is being started.

### B-EndingAWar
First token of a **EndingAWar** event span. The subclass of EndingConflict where an armed conflict between different groups of people, two or more countries, etc. is made to come to an end.

### I-EndingAWar
Non-initial (continuation) token of a **EndingAWar** event span, i.e. a token that continues an event of type EndingAWar begun by a preceding B-EndingAWar or I-EndingAWar token. The subclass of EndingConflict where an armed conflict between different groups of people, two or more countries, etc. is made to come to an end.

### B-Besieging
First token of a **Besieging** event span. The subclass of Attacking where some location is being surrounded and blocked by enemy troops with the aim to cause the surrender of the besieged.

### I-Besieging
Non-initial (continuation) token of a **Besieging** event span, i.e. a token that continues an event of type Besieging begun by a preceding B-Besieging or I-Besieging token. The subclass of Attacking where some location is being surrounded and blocked by enemy troops with the aim to cause the surrender of the besieged.

### B-Invasion
First token of a **Invasion** event span. The subclass of Attacking where some country or location is unwelcomely intruded by some armed forces.

### I-Invasion
Non-initial (continuation) token of a **Invasion** event span, i.e. a token that continues an event of type Invasion begun by a preceding B-Invasion or I-Invasion token. The subclass of Attacking where some country or location is unwelcomely intruded by some armed forces.

### B-Occupation
First token of a **Occupation** event span. Property where some group of people, e.g. military have control over some region, e.g. a country or a building.

### I-Occupation
Non-initial (continuation) token of a **Occupation** event span, i.e. a token that continues an event of type Occupation begun by a preceding B-Occupation or I-Occupation token. Property where some group of people, e.g. military have control over some region, e.g. a country or a building.

### B-TakingUnderControl
First token of a **TakingUnderControl** event span. The subclass of SocialInteraction where someone takes control over some person, group of persons or entity (ship).

### I-TakingUnderControl
Non-initial (continuation) token of a **TakingUnderControl** event span, i.e. a token that continues an event of type TakingUnderControl begun by a preceding B-TakingUnderControl or I-TakingUnderControl token. The subclass of SocialInteraction where someone takes control over some person, group of persons or entity (ship).

### B-Enslaving
First token of a **Enslaving** event span. The subclass of TakingUnderControl where someone takes control over some person or group of persons.

### I-Enslaving
Non-initial (continuation) token of a **Enslaving** event span, i.e. a token that continues an event of type Enslaving begun by a preceding B-Enslaving or I-Enslaving token. The subclass of TakingUnderControl where someone takes control over some person or group of persons.

### B-BeingDead
First token of a **BeingDead** event span. Property where some organism is dead.

### I-BeingDead
Non-initial (continuation) token of a **BeingDead** event span, i.e. a token that continues an event of type BeingDead begun by a preceding B-BeingDead or I-BeingDead token. Property where some organism is dead.

### B-Dying
First token of a **Dying** event span. The subclass of InternalChange where someone is dying, ultimately resulting in death.

### I-Dying
Non-initial (continuation) token of a **Dying** event span, i.e. a token that continues an event of type Dying begun by a preceding B-Dying or I-Dying token. The subclass of InternalChange where someone is dying, ultimately resulting in death.

### B-Killing
First token of a **Killing** event span. The subclass of Attacking where someone kills an animate being.

### I-Killing
Non-initial (continuation) token of a **Killing** event span, i.e. a token that continues an event of type Killing begun by a preceding B-Killing or I-Killing token. The subclass of Attacking where someone kills an animate being.

### B-BeingDestroyed
First token of a **BeingDestroyed** event span. Property where something is in a destroyed state.

### I-BeingDestroyed
Non-initial (continuation) token of a **BeingDestroyed** event span, i.e. a token that continues an event of type BeingDestroyed begun by a preceding B-BeingDestroyed or I-BeingDestroyed token. Property where something is in a destroyed state.

### B-Destroying
First token of a **Destroying** event span. The subclass of InternalChange where something gets destroyed.

### I-Destroying
Non-initial (continuation) token of a **Destroying** event span, i.e. a token that continues an event of type Destroying begun by a preceding B-Destroying or I-Destroying token. The subclass of InternalChange where something gets destroyed.

### B-Sinking
First token of a **Sinking** event span. DynamicEvent where a ship stops floating and submerges below the water surface.

### I-Sinking
Non-initial (continuation) token of a **Sinking** event span, i.e. a token that continues an event of type Sinking begun by a preceding B-Sinking or I-Sinking token. DynamicEvent where a ship stops floating and submerges below the water surface.

### B-HavingAMedicalCondition
First token of a **HavingAMedicalCondition** event span. Property where some human or animal suffers from a medical condition such as diseases, chronic diseases and disabilities.

### I-HavingAMedicalCondition
Non-initial (continuation) token of a **HavingAMedicalCondition** event span, i.e. a token that continues an event of type HavingAMedicalCondition begun by a preceding B-HavingAMedicalCondition or I-HavingAMedicalCondition token. Property where some human or animal suffers from a medical condition such as diseases, chronic diseases and disabilities.

### B-Healing
First token of a **Healing** event span. The subclass of ScalarChange where a human or animal heals after some injury or illness.

### I-Healing
Non-initial (continuation) token of a **Healing** event span, i.e. a token that continues an event of type Healing begun by a preceding B-Healing or I-Healing token. The subclass of ScalarChange where a human or animal heals after some injury or illness.

### B-FallingIll
First token of a **FallingIll** event span. The subclass of ScalarChange where a human or animal falls ill or suffers an injury.

### I-FallingIll
Non-initial (continuation) token of a **FallingIll** event span, i.e. a token that continues an event of type FallingIll begun by a preceding B-FallingIll or I-FallingIll token. The subclass of ScalarChange where a human or animal falls ill or suffers an injury.

### B-BeingDamaged
First token of a **BeingDamaged** event span. Static event where some entity is in a damaged state

### I-BeingDamaged
Non-initial (continuation) token of a **BeingDamaged** event span, i.e. a token that continues an event of type BeingDamaged begun by a preceding B-BeingDamaged or I-BeingDamaged token. Static event where some entity is in a damaged state

### B-Repairing
First token of a **Repairing** event span. The subclass of ScalarChange where some tangible object is modified in such way that it works properly again or can be taken back into it's intended function.

### I-Repairing
Non-initial (continuation) token of a **Repairing** event span, i.e. a token that continues an event of type Repairing begun by a preceding B-Repairing or I-Repairing token. The subclass of ScalarChange where some tangible object is modified in such way that it works properly again or can be taken back into it's intended function.

### B-Damaging
First token of a **Damaging** event span. The subclass of ScalarChange where some tangible entity gets damaged.

### I-Damaging
Non-initial (continuation) token of a **Damaging** event span, i.e. a token that continues an event of type Damaging begun by a preceding B-Damaging or I-Damaging token. The subclass of ScalarChange where some tangible entity gets damaged.

### B-Punishing
First token of a **Punishing** event span. The subclass of SocialInteraction where a person or group of people gets punished, which could be in the form of a physical attack, official sentencing in some type of court or any other punishment inflicted by some authority on an individual or set of individuals.

### I-Punishing
Non-initial (continuation) token of a **Punishing** event span, i.e. a token that continues an event of type Punishing begun by a preceding B-Punishing or I-Punishing token. The subclass of SocialInteraction where a person or group of people gets punished, which could be in the form of a physical attack, official sentencing in some type of court or any other punishment inflicted by some authority on an individual or set of individuals.

### B-HavingInternalState+
First token of a **HavingInternalState+** event span. Static event where someone or something (which can also be something intangible) is in a better state relatively to an earlier moment.

### I-HavingInternalState+
Non-initial (continuation) token of a **HavingInternalState+** event span, i.e. a token that continues an event of type HavingInternalState+ begun by a preceding B-HavingInternalState+ or I-HavingInternalState+ token. Static event where someone or something (which can also be something intangible) is in a better state relatively to an earlier moment.

### B-HavingInternalState-
First token of a **HavingInternalState-** event span. Static event where someone or something (which can also be something intangible) is in a worse state relatively to an earlier moment

### I-HavingInternalState-
Non-initial (continuation) token of a **HavingInternalState-** event span, i.e. a token that continues an event of type HavingInternalState- begun by a preceding B-HavingInternalState- or I-HavingInternalState- token. Static event where someone or something (which can also be something intangible) is in a worse state relatively to an earlier moment
